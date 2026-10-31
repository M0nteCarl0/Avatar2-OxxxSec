#!/usr/bin/env python3
"""
Post 19: Automated Unknown Peripheral Address Discovery & Mapping
Real firmware sweeps an MMIO window; the modeled bus fabric answers with device IDs.
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
BUS_BASE = 0x40000000
BUS_SIZE = 0x20000
SCAN_START = 0x4000C000
SCAN_STEP = 0x1000
SCAN_SLOTS = 8

KNOWN_DEVICES = {
    0x4000C000: (0xCAFE0002, "PL011 UART"),
    0x40010000: (0xCAFE0001, "Crypto accelerator"),
}

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


class VirtualBusFabric(AvatarPeripheral):
    """Peripheral bus matrix: only addresses with an attached device return a device ID.

      0x00 of every 4 KB slot is the read-only DEVICE_ID register.  Unattached slots read as 0.
    """

    def __init__(self, name, address, size, devices):
        super().__init__(name, address, size)
        self.devices = devices
        self.read_handler[0x00:size] = self.read_bus
        self.write_handler[0x00:size] = self.write_bus
        self.probes = []

    def _slot(self, offset):
        return self.address + (offset & ~0xFFF)

    def read_bus(self, offset, size, pc=0):
        slot = self._slot(offset)
        within = offset & 0xFFF
        device = self.devices.get(slot)
        value = device[0] if device is not None and within == 0 else 0
        self.probes.append((slot, value, pc))
        print(f"[BUS] Probe 0x{slot:08x} -> 0x{value:08x} "
              f"({'HIT: ' + device[1] if value else 'no device'})")
        return value

    def write_bus(self, offset, size, value, pc=0):
        slot = self._slot(offset)
        if slot not in self.devices:
            print(f"[BUS] Write to empty slot 0x{slot:08x} ignored")
        return True


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x4000C000      @ first candidate slot
        ldr  r5, =0x20000000      @ results array in SRAM
        movs r6, #0
        movs r7, #8
    scan:
        ldr  r0, [r4]             @ read DEVICE_ID of the candidate slot
        str  r0, [r5]             @ record the discovery result
        adds r5, #4
        add  r4, r4, #0x1000      @ next 4 KB slot
        adds r6, #1
        cmp  r6, r7
        bne  scan
        b    .
        """
    )
    return bytes(code)


def run_discovery_demo() -> None:
    print("[*] Initializing Automated Peripheral Discovery...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_disco_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        bus = VirtualBusFabric("bus", BUS_BASE, BUS_SIZE, KNOWN_DEVICES)
        ava.add_memory_range(BUS_BASE, BUS_SIZE, name="peripheral_bus", permissions="rw-",
                             forwarded=True, forwarded_to=bus)
        ava.init_targets()
        print(f"[+] Bus fabric modeled over 0x{BUS_BASE:08x}..0x{BUS_BASE + BUS_SIZE - 1:08x}")
        print(f"[*] Devices attached (unknown to the firmware): "
              f"{ {hex(k): v[1] for k, v in KNOWN_DEVICES.items()} }")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(BUS_BASE, BUS_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, bus, BUS_BASE, BUS_SIZE)

        print("[*] Firmware sweeping the bus for live peripherals...")
        uc.emu_start(FLASH_BASE | 1, 0, count=600)

        raw_results = []
        for index in range(SCAN_SLOTS):
            value = int.from_bytes(bytes(uc.mem_read(RAM_BASE + index * 4, 4)), "little")
            raw_results.append((SCAN_START + index * SCAN_STEP, value))

        discovered = {}
        for slot, value in raw_results:
            if value:
                discovered[slot] = value

        print("[+] Scan results written by firmware:")
        for slot, value in raw_results:
            name = next((d[1] for d in KNOWN_DEVICES.values() if d[0] == value), "unmapped")
            print(f"  0x{slot:08x} : 0x{value:08x}  [{name}]")
        print(f"[+] Discovered {len(discovered)} live peripheral(s) out of {SCAN_SLOTS} slots probed")
        print(f"[+] Bus probes observed: {len(bus.probes)}")

        assert len(discovered) == len(KNOWN_DEVICES)
        assert set(discovered) == set(KNOWN_DEVICES)
        assert all(discovered[slot] == KNOWN_DEVICES[slot][0] for slot in discovered)

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Peripheral discovery verified against real firmware sweep.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_discovery_demo()
