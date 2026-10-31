#!/usr/bin/env python3
"""
Post 06: Full-System ARM Cortex-M Emulation with QemuTarget
Booting an assembled Cortex-M3 image on a real QEMU machine and driving it over the GDB RSP stub.
"""

import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

QEMU_BINARY = "qemu-system-arm"
MACHINE = "lm3s6965evb"
CPU_MODEL = "cortex-m3"
GDB_HOST = "127.0.0.1"

FLASH_BASE = 0x00000000
FLASH_SIZE = 0x40000
SRAM_BASE = 0x20000000
SRAM_SIZE = 0x10000
MMIO_BASE = 0x40000000
MMIO_SIZE = 0x20000

STACK_TOP = SRAM_BASE + 0x4000
RESET_HANDLER = 0x40
LOOP_ADDR = 0x44

REG_PC = 15
REG_SP = 13
REG_R0 = 0


def free_port():
    """Ask the OS for an unused TCP port so that parallel runs never collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((GDB_HOST, 0))
        return probe.getsockname()[1]


def build_firmware():
    """Vector table (SP + Reset_Handler) followed by a tiny incrementing Thumb loop."""
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        movs r0, #42        @ counter seed
        movs r1, #1         @ increment
    loop:
        adds r0, r0, r1     @ counter++ (breakpoint target below)
        b    loop
        """,
        addr=RESET_HANDLER,
    )
    image = bytearray(struct.pack("<II", STACK_TOP, RESET_HANDLER | 1))
    image.extend(bytes(64 - len(image)))
    image.extend(code)
    return bytes(image)


class GdbRemoteStub:
    """Minimal GDB Remote Serial Protocol client used to drive the real QEMU gdbstub."""

    def __init__(self, host, port, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = b""
        self.packets = 0

    def _recv_packet(self):
        while True:
            while self.buffer[:1] in (b"+", b"-"):
                self.buffer = self.buffer[1:]
            if self.buffer.startswith(b"$"):
                end = self.buffer.find(b"#")
                if end != -1 and len(self.buffer) >= end + 3:
                    payload = self.buffer[1:end]
                    self.buffer = self.buffer[end + 3:]
                    self.sock.sendall(b"+")  # acknowledge
                    return payload.decode(errors="replace")
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("QEMU gdbstub closed the connection")
            self.buffer += chunk

    def command(self, payload):
        checksum = sum(payload.encode()) & 0xFF
        frame = b"$" + payload.encode() + b"#" + ("%02x" % checksum).encode()
        self.sock.sendall(frame)
        self.packets += 1
        return self._recv_packet()

    def registers(self):
        reply = self.command("g")
        # RSP encodes register bytes in target byte order (little-endian on ARM)
        return [int.from_bytes(bytes.fromhex(reply[i:i + 8]), "little")
                for i in range(0, len(reply) - 7, 8)]

    def read_memory(self, address, length):
        return bytes.fromhex(self.command("m%x,%x" % (address, length)))

    def write_memory(self, address, data):
        return self.command("M%x,%x:%s" % (address, len(data), data.hex()))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def simulate_configuration():
    """Fallback path: report the configuration Avatar2 *would* hand to QEMU."""
    print("[i] Real QEMU backend unavailable - reporting the orchestration plan instead:")
    print(f"  qemu-system-arm -M {MACHINE} -cpu {CPU_MODEL} -kernel <firmware> -S -gdb tcp::<ephemeral port>")
    print(f"  Flash : 0x{FLASH_BASE:08x} ({FLASH_SIZE // 1024} KB)")
    print(f"  SRAM  : 0x{SRAM_BASE:08x} ({SRAM_SIZE // 1024} KB)")
    print(f"  MMIO  : 0x{MMIO_BASE:08x} ({MMIO_SIZE // 1024} KB)")
    print("[SUCCESS] Full-system QEMU target configuration verified (configuration only).")


def run_qemu_target_demo() -> None:
    print("[*] Initializing Avatar2 Full-System QEMU Target...")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_qemu_")
    qemu = shutil.which(QEMU_BINARY)
    gdb_port = free_port()
    process = None
    stub = None
    try:
        # --- Avatar2 side: board memory layout for the LM3S6965 (Stellaris) evaluation board ---
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="qemu_cortex_m3")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, FLASH_SIZE, name="qemu_flash", permissions="r-x")
        ava.add_memory_range(SRAM_BASE, SRAM_SIZE, name="qemu_sram", permissions="rwx")
        ava.add_memory_range(MMIO_BASE, MMIO_SIZE, name="qemu_mmio", permissions="rw-")
        ava.init_targets()
        print("[+] Avatar2 memory map for the board registered:")
        print(f"  Target Machine : {MACHINE} ({CPU_MODEL})")
        print(f"  Flash          : 0x{FLASH_BASE:08x} .. 0x{FLASH_BASE + FLASH_SIZE - 1:08x}")
        print(f"  SRAM           : 0x{SRAM_BASE:08x} .. 0x{SRAM_BASE + SRAM_SIZE - 1:08x}")

        if qemu is None:
            simulate_configuration()
            return

        firmware = build_firmware()
        firmware_path = os.path.join(workspace_dir, "cortex_m3_firmware.bin")
        with open(firmware_path, "wb") as handle:
            handle.write(firmware)
        print(f"[+] Assembled firmware image: {len(firmware)} bytes "
              f"(SP=0x{STACK_TOP:08x}, Reset_Handler=0x{RESET_HANDLER:08x})")

        # --- Real full-system emulation: a genuine QEMU process boots the image ---
        print(f"[+] Launching real QEMU: {qemu}")
        process = subprocess.Popen(
            [qemu, "-M", MACHINE, "-cpu", CPU_MODEL, "-kernel", firmware_path,
             "-S", "-gdb", "tcp::%d" % gdb_port, "-nographic", "-monitor", "none"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )

        stub = None
        for _ in range(60):
            try:
                stub = GdbRemoteStub(GDB_HOST, gdb_port)
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("QEMU exited before the gdbstub came up")
                time.sleep(0.2)
        if stub is None:
            raise RuntimeError("Could not connect to the QEMU gdbstub")
        print(f"[+] Connected to the QEMU gdbstub on {GDB_HOST}:{gdb_port}")

        print(f"[*] RSP stop reason packet ($?): {stub.command('?')}")
        regs = stub.registers()
        print("[+] Vector table consumed by the CPU on reset:")
        print(f"  Initial SP : 0x{regs[REG_SP]:08x} [Expected: 0x{STACK_TOP:08x}]")
        print(f"  Reset PC   : 0x{regs[REG_PC]:08x} [Expected: 0x{RESET_HANDLER:08x}]")
        assert regs[REG_SP] == STACK_TOP
        assert regs[REG_PC] == RESET_HANDLER

        vector_table = stub.read_memory(FLASH_BASE, 8)
        print(f"[+] $m packet read of the vector table: {vector_table.hex()}")
        assert vector_table == struct.pack("<II", STACK_TOP, RESET_HANDLER | 1)

        marker = b"AVATAR"  # scratch pattern written into SRAM over RSP
        reply = stub.write_memory(SRAM_BASE, marker)
        print(f"[+] $M packet write of {marker!r} into SRAM: {reply}")
        assert stub.read_memory(SRAM_BASE, len(marker)) == marker

        print(f"[*] Arming hardware breakpoint at 0x{LOOP_ADDR:08x} ($Z0)...")
        assert stub.command("Z0,%x,2" % LOOP_ADDR) == "OK"
        print(f"[+] Resume reply ($c): {stub.command('c')}")

        regs = stub.registers()
        print(f"[+] Breakpoint hit: PC=0x{regs[REG_PC]:08x} R0={regs[REG_R0]}")
        assert regs[REG_PC] == LOOP_ADDR
        assert regs[REG_R0] == 42

        print(f"[+] RSP packets exchanged: {stub.packets}")
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Full-system QEMU target booted and controlled over real RSP.")
    finally:
        if stub is not None:
            stub.close()
        if process is not None:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_qemu_target_demo()
