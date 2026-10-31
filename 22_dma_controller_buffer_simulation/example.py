#!/usr/bin/env python3
"""
Post 22: Direct Memory Access (DMA) Controller & Circular Buffer Simulation
Real firmware programs a modeled DMA channel; the model moves bytes through emulated memory.
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
DMA_BASE = 0x40026000
DMA_SIZE = 0x1000
PAYLOAD_OFFSET = 0x80
PAYLOAD = b"AVATAR2-DMA-POC!"

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


class VirtualDmaController(AvatarPeripheral):
    """
    Simple two-register DMA engine.
      0x00: Source address (SRC)
      0x04: Destination address (DST)
      0x08: Transfer length in bytes (LEN)
      0x0C: Control (CTRL)  [write 1 to start a transfer]
      0x10: Status (STAT)   [bit 1: done, bit 0: busy]
      0x14: Bytes transferred counter
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_src
        self.write_handler[0x04:0x08] = self.write_dst
        self.write_handler[0x08:0x0C] = self.write_len
        self.write_handler[0x0C:0x10] = self.write_ctrl
        self.read_handler[0x10:0x14] = self.read_status
        self.read_handler[0x14:0x18] = self.read_count

        self.src = 0
        self.dst = 0
        self.length = 0
        self.status = 0x02  # done / idle
        self.transferred = 0
        self.memory_reader = None  # set by the demo: guest memory -> bytes
        self.memory_writer = None  # set by the demo: bytes -> guest memory

    def write_src(self, offset, size, value, pc=0):
        self.src = value
        print(f"[DMA] SRC <- 0x{value:08x}")
        return True

    def write_dst(self, offset, size, value, pc=0):
        self.dst = value
        print(f"[DMA] DST <- 0x{value:08x}")
        return True

    def write_len(self, offset, size, value, pc=0):
        self.length = value
        print(f"[DMA] LEN <- {value} bytes")
        return True

    def write_ctrl(self, offset, size, value, pc=0):
        if value & 1 and self.memory_reader and self.memory_writer:
            self.status = 0x01  # busy
            payload = self.memory_reader(self.src, self.length)
            self.memory_writer(self.dst, payload)
            self.transferred += len(payload)
            self.status = 0x02  # done
            print(f"[DMA] Transfer complete: {bytes(payload)!r} -> 0x{self.dst:08x}")
        return True

    def read_status(self, offset, size, pc=0):
        print(f"[DMA] Status polled from PC 0x{pc:08x}: 0x{self.status:08x}")
        return self.status

    def read_count(self, offset, size, pc=0):
        return self.transferred & 0xFFFFFFFF


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40026000          @ DMA controller base
        ldr  r0, =0x08000080          @ source buffer inside flash
        str  r0, [r4, #0x00]
        ldr  r0, =0x20000100          @ destination buffer in SRAM
        str  r0, [r4, #0x04]
        movs r0, #16
        str  r0, [r4, #0x08]
        movs r0, #1
        str  r0, [r4, #0x0C]          @ kick off the transfer
    poll:
        ldr  r5, [r4, #0x10]          @ poll the status register
        tst  r5, #0x02
        beq  poll
        ldr  r6, [r4, #0x14]          @ bytes transferred
        ldr  r7, =0x20000000
        str  r6, [r7]
        b    .
        """
    )
    image = bytearray(code)
    image.extend(bytes(PAYLOAD_OFFSET - len(image)))
    image.extend(PAYLOAD)
    return bytes(image)


def run_dma_demo() -> None:
    print("[*] Initializing DMA Controller Simulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_dma_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        dma = VirtualDmaController("dma1", DMA_BASE, DMA_SIZE)
        ava.add_memory_range(DMA_BASE, DMA_SIZE, name="dma_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=dma)
        ava.init_targets()
        print(f"[+] DMA controller mapped at 0x{DMA_BASE:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(DMA_BASE, DMA_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        dma.memory_reader = lambda address, length: bytes(uc.mem_read(address, length))
        dma.memory_writer = lambda address, data: uc.mem_write(address, bytes(data))
        bridge = MmioBridge(uc, dma, DMA_BASE, DMA_SIZE)

        print("[*] Executing firmware that programs the DMA channel...")
        uc.emu_start(FLASH_BASE | 1, 0, count=400)

        copied = bytes(uc.mem_read(RAM_BASE + 0x100, len(PAYLOAD)))
        transferred = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        stashed = int.from_bytes(bytes(uc.mem_read(RAM_BASE, 4)), "little")

        print(f"[+] MMIO writes / reads : {len(bridge.writes)} / {len(bridge.reads)}")
        print(f"[+] Copied buffer in RAM: {copied!r}")
        print(f"[+] Bytes transferred   : {transferred} (stashed by firmware: {stashed})")
        print(f"[+] Channel status      : 0x{dma.status:08x} (DONE)")

        assert copied == PAYLOAD, "DMA did not move the payload"
        assert transferred == stashed == len(PAYLOAD)
        assert dma.status & 0x02

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] DMA controller simulation verified against real firmware execution.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_dma_demo()
