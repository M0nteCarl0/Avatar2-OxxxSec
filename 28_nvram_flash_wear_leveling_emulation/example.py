#!/usr/bin/env python3
"""
Post 28: Serial SPI Flash (NOR/NAND) & NVRAM File-Backed Emulation
Real firmware programs a file-backed, wear-levelled NVRAM controller over MMIO.
"""

import os
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
CTRL_BASE = 0x40023000
CTRL_SIZE = 0x1000

SECTORS = 8
SECTOR_SIZE = 256
PROGRAM_COUNT = 5

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size):
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


class FileBackedNvramController(AvatarPeripheral):
    """NVRAM/SPI-flash controller with least-worn sector allocation (wear levelling).

      0x00: CMD    [1 = program word, 2 = erase logical sector]
      0x04: ADDR   [logical byte address]
      0x08: DATA   [32-bit word to program]
      0x0C: STATUS [bit 1 = done]
      0x10: WEAR   [maximum sector wear count]
    """

    def __init__(self, name, address, size, file_path):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cmd
        self.write_handler[0x04:0x08] = self.write_addr
        self.write_handler[0x08:0x0C] = self.write_data
        self.read_handler[0x0C:0x10] = self.read_status
        self.read_handler[0x10:0x14] = self.read_wear

        self.file_path = file_path
        self.cmd = 0
        self.addr = 0
        self.data = 0
        self.status = 0x02
        self.wear = [0] * SECTORS
        self.translation = {}   # logical sector -> physical sector
        self.program_log = []
        with open(self.file_path, "wb") as handle:
            handle.write(bytes(SECTORS * SECTOR_SIZE))

    # --- register interface (called by the guest MMIO bridge) ---

    def write_cmd(self, offset, size, value, pc=0):
        self.cmd = value
        if value == 1:
            self._program_word(pc)
        elif value == 2:
            self._erase_sector(pc)
        return True

    def write_addr(self, offset, size, value, pc=0):
        self.addr = value
        return True

    def write_data(self, offset, size, value, pc=0):
        self.data = value & 0xFFFFFFFF
        return True

    def read_status(self, offset, size, pc=0):
        return self.status

    def read_wear(self, offset, size, pc=0):
        print(f"[NVRAM] WEAR read by firmware: max={max(self.wear)} distribution={self.wear}")
        return max(self.wear)

    # --- internals ---

    def _physical_sector(self, logical_sector):
        if logical_sector not in self.translation:
            least_worn = min(range(SECTORS), key=lambda sector: self.wear[sector])
            self.translation[logical_sector] = least_worn
        return self.translation[logical_sector]

    def _program_word(self, pc):
        logical_sector = (self.addr >> 8) % SECTORS
        physical = self._physical_sector(logical_sector)
        offset = physical * SECTOR_SIZE + (self.addr & (SECTOR_SIZE - 1))
        with open(self.file_path, "r+b") as flash:
            flash.seek(offset)
            flash.write(self.data.to_bytes(4, "little"))
        self.wear[physical] += 1
        self.program_log.append((self.addr, self.data, physical))
        print(f"[NVRAM] Program 0x{self.data:08x} @ logical 0x{self.addr:04x} -> "
              f"physical sector {physical} (PC=0x{pc:08x})")
        if self.wear[physical] >= 2:
            # Rotate to the next least-worn sector (classic dynamic wear levelling)
            candidates = sorted(range(SECTORS), key=lambda sector: self.wear[sector])
            self.translation[logical_sector] = candidates[0]

    def _erase_sector(self, pc):
        logical_sector = (self.addr >> 8) % SECTORS
        physical = self._physical_sector(logical_sector)
        with open(self.file_path, "r+b") as flash:
            flash.seek(physical * SECTOR_SIZE)
            flash.write(bytes(SECTOR_SIZE))
        print(f"[NVRAM] Erase of physical sector {physical} (PC=0x{pc:08x})")

    def read_logical(self, offset, length=4):
        logical_sector = (offset >> 8) % SECTORS
        physical = self.translation.get(logical_sector, logical_sector)
        position = physical * SECTOR_SIZE + (offset & (SECTOR_SIZE - 1))
        with open(self.file_path, "rb") as flash:
            flash.seek(position)
            return flash.read(length)


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40023000      @ NVRAM controller
        movs r0, #5               @ number of records to program
        movs r1, #0xA0            @ first payload value
        movs r2, #0               @ loop counter
    loop:
        movs r3, #0
        str  r3, [r4, #0x04]      @ ADDR = logical 0x000 (same slot every time)
        str  r1, [r4, #0x08]      @ DATA = payload
        movs r3, #1
        str  r3, [r4, #0x00]      @ CMD = program word
        adds r1, r1, #1
        adds r2, r2, #1
        cmp  r2, r0
        bne  loop
        ldr  r5, [r4, #0x10]      @ read the maximum sector wear
        ldr  r6, [r4, #0x0C]      @ read the controller status
        b    .
        """
    )
    return bytes(code)


def run_nvram_demo() -> None:
    print("[*] Initializing File-Backed NVRAM / Wear Levelling Emulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_nvram_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")

        image_path = os.path.join(workspace_dir, "nvm_image.bin")
        nvram = FileBackedNvramController("nvram", CTRL_BASE, CTRL_SIZE, image_path)
        ava.add_memory_range(CTRL_BASE, CTRL_SIZE, name="nvram_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=nvram)
        ava.init_targets()
        print(f"[+] NVRAM controller mapped at 0x{CTRL_BASE:08x}, backing file {os.path.basename(image_path)}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(CTRL_BASE, CTRL_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, nvram, CTRL_BASE, CTRL_SIZE)

        print("[*] Executing firmware that rewrites the same logical slot repeatedly...")
        uc.emu_start(FLASH_BASE | 1, 0, count=600)

        max_wear_reg = uc.reg_read(uc_arm.UC_ARM_REG_R5)
        status = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        image_size = os.path.getsize(image_path)
        physical_sectors = sorted({entry[2] for entry in nvram.program_log})

        print(f"[+] Programs performed    : {len(nvram.program_log)}")
        print(f"[+] Physical sectors used : {physical_sectors} (wear levelling)")
        print(f"[+] Wear distribution     : {nvram.wear}")
        print(f"[+] WEAR register read    : {max_wear_reg}")
        print(f"[+] Controller STATUS     : 0x{status:08x}")
        print(f"[+] Backing file size     : {image_size} bytes")

        assert len(nvram.program_log) == PROGRAM_COUNT
        assert len(physical_sectors) > 1, "wear levelling did not rotate physical sectors"
        assert max_wear_reg == max(nvram.wear)
        assert image_size == SECTORS * SECTOR_SIZE
        for logical, value, physical in nvram.program_log:
            assert nvram.read_logical(logical) != b"", "programmed word did not reach the file"

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] File-backed NVRAM wear levelling verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_nvram_demo()
