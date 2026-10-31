#!/usr/bin/env python3
"""
Post 08: Custom MMIO Peripheral Modeling with AvatarPeripheral
A real Cortex-M3 core (Unicorn JIT) drives a stateful Python MMIO crypto accelerator.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
ACCEL_BASE = 0x40010000
ACCEL_SIZE = 0x1000

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Routes guest MMIO traffic into an AvatarPeripheral.

    Writes are dispatched directly through the hook; reads are served by the peripheral and the
    loaded destination register is patched on the next instruction hook (Unicorn cannot rewrite
    a load result from inside a memory-read hook).
    """

    def __init__(self, uc, peripheral, base, size):
        self.uc = uc
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class CustomCryptoAccelerator(AvatarPeripheral):
    """
    Hardware Cryptographic Hash Accelerator.
      0x00: Control Register (CR)  [Bit 0: Enable, Bit 1: Start Hash, Bit 2: Reset]
      0x04: Status Register (SR)   [Bit 0: Busy, Bit 1: Done, Bit 2: Error]
      0x08: Data In Register (DIN) [Accumulate data bytes]
      0x0C: Digest Output (DOUT)   [32-bit hash result]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x00:0x04] = self.read_cr
        self.write_handler[0x00:0x04] = self.write_cr
        self.read_handler[0x04:0x08] = self.read_sr
        self.write_handler[0x04:0x08] = self.write_sr
        self.write_handler[0x08:0x0C] = self.write_din
        self.read_handler[0x0C:0x10] = self.read_dout

        self.cr = 0
        self.sr = 0x02  # DONE / IDLE
        self.accumulated_data = bytearray()
        self.digest = 0x1337BEEF

    def read_cr(self, offset, size, pc=0):
        return self.cr

    def write_cr(self, offset, size, value, pc=0):
        self.cr = value
        print(f"[ACCELERATOR CR] Write: 0x{value:08x} (PC: 0x{pc:08x})")
        if value & (1 << 2):  # Reset
            self.accumulated_data.clear()
            self.sr = 0x02
            print("  [*] Accelerator state cleared by firmware")
        if value & (1 << 1):  # Start hash
            print(f"  [*] Hashing {len(self.accumulated_data)} accumulated bytes...")
            self.digest = 0x1337BEEF ^ len(self.accumulated_data)
            for byte in self.accumulated_data:
                self.digest = (((self.digest << 5) | (self.digest >> 27)) ^ byte) & 0xFFFFFFFF
            self.sr = 0x02  # DONE
            print(f"  [*] Digest ready: 0x{self.digest:08x}")
        return True

    def read_sr(self, offset, size, pc=0):
        print(f"[ACCELERATOR SR] Status polled from PC 0x{pc:08x}: 0x{self.sr:08x}")
        return self.sr

    def write_sr(self, offset, size, value, pc=0):
        self.sr &= ~value  # write-1-to-clear
        return True

    def write_din(self, offset, size, value, pc=0):
        byte_val = value & 0xFF
        self.accumulated_data.append(byte_val)
        printable = chr(byte_val) if 32 <= byte_val < 127 else "."
        print(f"[ACCELERATOR DIN] Byte 0x{byte_val:02x} ('{printable}') from PC 0x{pc:08x}")
        return True

    def read_dout(self, offset, size, pc=0):
        print(f"[ACCELERATOR DOUT] Firmware read digest: 0x{self.digest:08x}")
        return self.digest


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40010000      @ accelerator base
        movs r0, #0x4B            @ 'K'
        str  r0, [r4, #0x08]
        movs r0, #0x45            @ 'E'
        str  r0, [r4, #0x08]
        movs r0, #0x59            @ 'Y'
        str  r0, [r4, #0x08]
        movs r0, #0x21            @ '!'
        str  r0, [r4, #0x08]
        movs r0, #2               @ CR: start hash
        str  r0, [r4, #0x00]
        ldr  r5, [r4, #0x04]      @ poll the status register
        ldr  r6, [r4, #0x0C]      @ read the digest output register
        ldr  r7, =0x20000040      @ stash it in RAM
        str  r6, [r7]
        b    .
        """
    )
    return bytes(code)


def run_peripheral_modeling_demo() -> None:
    print("[*] Initializing Custom MMIO Peripheral Model...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_periph_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)

        accelerator = CustomCryptoAccelerator("crypto_accel", ACCEL_BASE, ACCEL_SIZE)
        ava.add_memory_range(ACCEL_BASE, ACCEL_SIZE, name="crypto_accel_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=accelerator)
        ava.init_targets()
        print(f"[+] Custom peripheral '{accelerator.name}' mapped at 0x{ACCEL_BASE:08x}")

        # --- Real CPU: the firmware below is genuinely executed by the Unicorn JIT engine ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(ACCEL_BASE, ACCEL_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, accelerator, ACCEL_BASE, ACCEL_SIZE)

        print("[*] Executing firmware on the JIT engine (real MMIO transactions)...")
        uc.emu_start(FLASH_BASE | 1, 0, count=200)

        status = uc.reg_read(uc_arm.UC_ARM_REG_R5)
        digest_reg = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        stashed = int.from_bytes(bytes(uc.mem_read(RAM_BASE + 0x40, 4)), "little")

        print(f"[+] Bytes pushed by firmware : {bytes(accelerator.accumulated_data)!r}")
        print(f"[+] MMIO writes / reads seen : {len(bridge.writes)} / {len(bridge.reads)}")
        print(f"[+] Digest (peripheral model): 0x{accelerator.digest:08x}")
        print(f"[+] Digest (guest register)  : 0x{digest_reg:08x}")
        print(f"[+] Digest (guest RAM copy)  : 0x{stashed:08x}")
        print(f"[+] Status read by firmware  : 0x{status:08x} (DONE bit set)")

        assert bytes(accelerator.accumulated_data) == b"KEY!"
        assert digest_reg == stashed == accelerator.digest
        assert status & 0x02
        assert any(address == ACCEL_BASE + 0x0C for address, _s, _v, _p in bridge.reads)

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Custom MMIO peripheral modeling verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_peripheral_modeling_demo()
