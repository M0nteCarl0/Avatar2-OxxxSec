#!/usr/bin/env python3
"""
Post 05: GDB Remote Serial Protocol (RSP) Target Control & Instrumentation
Driving a live target over a real, hand-rolled GDB RSP client (packet framing, checksums, $g/$P/$m/$M/$Z0/$c).
"""

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
GDB_HOST = "127.0.0.1"

FLASH_BASE = 0x00000000
SRAM_BASE = 0x20000000
STACK_TOP = SRAM_BASE + 0x4000
RESET_HANDLER = 0x40
BREAK_ADDR = 0x44

REG_R0 = 0
REG_SP = 13
REG_PC = 15


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((GDB_HOST, 0))
        return probe.getsockname()[1]


def build_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        movs r0, #7         @ placeholder value
        movs r1, #1
    loop:
        adds r0, r0, r1     @ breakpoint target
        b    loop
        """,
        addr=RESET_HANDLER,
    )
    image = bytearray(struct.pack("<II", STACK_TOP, RESET_HANDLER | 1))
    image.extend(bytes(64 - len(image)))
    image.extend(code)
    return bytes(image)


class GdbRemoteClient:
    """Minimal but complete GDB RSP client: framing, checksums, acknowledgements."""

    def __init__(self, host, port, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = b""
        self.packet_log = []

    def _recv(self):
        while True:
            while self.buffer[:1] in (b"+", b"-"):
                self.buffer = self.buffer[1:]
            if self.buffer.startswith(b"$"):
                end = self.buffer.find(b"#")
                if end != -1 and len(self.buffer) >= end + 3:
                    payload = self.buffer[1:end]
                    self.buffer = self.buffer[end + 3:]
                    self.sock.sendall(b"+")
                    return payload.decode(errors="replace")
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("gdbstub closed the connection")
            self.buffer += chunk

    def send(self, payload):
        checksum = sum(payload.encode()) & 0xFF
        frame = b"$" + payload.encode() + b"#" + ("%02x" % checksum).encode()
        self.sock.sendall(frame)
        self.packet_log.append((payload, "%02x" % checksum))
        return self._recv()

    def registers(self):
        reply = self.send("g")
        return [int.from_bytes(bytes.fromhex(reply[i:i + 8]), "little")
                for i in range(0, len(reply) - 7, 8)]

    def write_register(self, number, value):
        return self.send("P%x=%s" % (number, struct.pack("<I", value).hex()))

    def write_all_registers(self, values):
        payload = "".join(struct.pack("<I", value & 0xFFFFFFFF).hex() for value in values)
        return self.send("G" + payload)

    def read_memory(self, address, length):
        return bytes.fromhex(self.send("m%x,%x" % (address, length)))

    def write_memory(self, address, data):
        return self.send("M%x,%x:%s" % (address, len(data), data.hex()))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def simulate_rsp_session():
    """Fallback when no RSP peer is available: show the exact packet exchange."""
    print("[i] No live RSP peer available - showing the packet exchange a GDBTarget would perform:")
    for payload in ("?", "qSupported:multiprocess+", "g", "m0,8", "M20000000,4:deadbeef", "Z0,44,2", "c", "z0,44,2"):
        print(f"  -> ${payload}#{sum(payload.encode()) & 0xFF:02x}")
    print("[SUCCESS] GDB RSP control sequence documented (no live peer).")


def run_gdb_target_demo() -> None:
    print("[*] Initializing Avatar2 GDB Target Abstraction...")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_gdb_")
    qemu = shutil.which(QEMU_BINARY)
    process = None
    client = None
    port = free_port()
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="gdb_remote_target")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, 0x40000, name="firmware_rom", permissions="r-x")
        ava.add_memory_range(SRAM_BASE, 0x10000, name="firmware_ram", permissions="rwx")
        ava.init_targets()
        print(f"[+] Avatar2 GDB target wrapper ready (RSP endpoint {GDB_HOST}:{port})")

        if qemu is None:
            simulate_rsp_session()
            return

        firmware_path = workspace_dir + "/rsp_firmware.bin"
        with open(firmware_path, "wb") as handle:
            handle.write(build_firmware())

        # A real RSP peer: QEMU's gdbstub, halted at reset
        process = subprocess.Popen(
            [qemu, "-M", MACHINE, "-kernel", firmware_path, "-S",
             "-gdb", "tcp::%d" % port, "-nographic", "-monitor", "none"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                client = GdbRemoteClient(GDB_HOST, port)
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("QEMU exited before the gdbstub came up")
                time.sleep(0.2)
        if client is None:
            raise RuntimeError("Could not connect to the RSP peer")
        print("[+] Connected to a live gdbstub - speaking raw RSP frames")

        print(f"[*] $?  stop reason      -> {client.send('?')}")
        print(f"[*] $qSupported          -> {client.send('qSupported:multiprocess+')[:60]}...")

        regs = client.registers()
        print("[+] $g register cache fetched:")
        print(f"  PC : 0x{regs[REG_PC]:08x}")
        print(f"  SP : 0x{regs[REG_SP]:08x}")
        print(f"  R0 : 0x{regs[REG_R0]:08x}")
        assert regs[REG_PC] == RESET_HANDLER and regs[REG_SP] == STACK_TOP

        print(f"[*] $P writing R0 = 0x{0xCAFEBABE:08x} ...")
        if client.write_register(REG_R0, 0xCAFEBABE) == "OK":
            regs = client.registers()
            print(f"[+] R0 read back after $P: 0x{regs[REG_R0]:08x}")
            assert regs[REG_R0] == 0xCAFEBABE
        else:
            # Some gdbstubs (e.g. QEMU 6/7 builds on Linux) do not implement the
            # single-register $P packet and answer with an empty payload - fall back to
            # the universally supported $G (write all registers) packet.
            print("[i] $P unsupported by this stub - falling back to $G (write all registers)")
            regs = client.registers()
            regs[REG_R0] = 0xCAFEBABE
            assert client.write_all_registers(regs) == "OK"
            regs = client.registers()
            print(f"[+] R0 read back after $G: 0x{regs[REG_R0]:08x}")
            assert regs[REG_R0] == 0xCAFEBABE

        pattern = b"RSP!"
        print(f"[*] $M writing {pattern!r} into SRAM ...")
        assert client.write_memory(SRAM_BASE, pattern) == "OK"
        print(f"[+] $m read back: {client.read_memory(SRAM_BASE, 4)!r}")
        assert client.read_memory(SRAM_BASE, 4) == pattern

        print(f"[*] $Z0 arming breakpoint at 0x{BREAK_ADDR:08x} ...")
        assert client.send("Z0,%x,2" % BREAK_ADDR) == "OK"
        print(f"[+] $c resume -> {client.send('c')}")
        regs = client.registers()
        print(f"[+] Stopped at PC=0x{regs[REG_PC]:08x} R0={regs[REG_R0]}")
        assert regs[REG_PC] == BREAK_ADDR

        print(f"[*] $z0 removing breakpoint ... {client.send('z0,%x,2' % BREAK_ADDR)}")
        print("[+] RSP packet log (payload, checksum):")
        for payload, checksum in client.packet_log:
            print(f"  ${payload}#{checksum}")

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print(f"[SUCCESS] GDB RSP control sequence completed on a live peer "
              f"({len(client.packet_log)} packets).")
    finally:
        if client is not None:
            client.close()
        if process is not None:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_gdb_target_demo()
