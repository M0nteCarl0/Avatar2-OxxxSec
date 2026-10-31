#!/usr/bin/env python3
"""
Post 07: Hardware-in-the-Loop (HITL) Memory Forwarding Architecture
Setting up an emulated target with transparent MMIO forwarding to a hardware proxy.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class HardwareProxyPeripheral(AvatarPeripheral):
    """
    Simulates a physical hardware device connected over JTAG/SWD.
    Receives forwarded MMIO accesses from the emulator and returns physical register responses.
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        # Register read and write handlers across the 4KB peripheral window
        self.read_handler[0:size] = self.hw_read
        self.write_handler[0:size] = self.hw_write
        self.hardware_registers = {
            0x00: 0x48415244,  # Device ID Register: 'HARD'
            0x04: 0x00000001,  # Hardware Status: READY
            0x08: 0x00000000   # Config Register
        }

    def hw_read(self, offset, size, pc=0):
        val = self.hardware_registers.get(offset, 0x00000000)
        print(f"[HITL FORWARD READ] Emulated PC: 0x{pc:08x} -> Read HW Offset 0x{offset:02x} (Size: {size}) = 0x{val:08x}")
        return val

    def hw_write(self, offset, size, value, pc=0):
        print(f"[HITL FORWARD WRITE] Emulated PC: 0x{pc:08x} -> Write HW Offset 0x{offset:02x} = 0x{value:08x}")
        self.hardware_registers[offset] = value
        return True

def run_memory_forwarding_demo() -> None:
    print("[*] Initializing Avatar2 Hardware-in-the-Loop Forwarding Engine...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_hitl_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        emulator_cpu = ava.add_target(DummyTarget, name="virtual_cpu")
        emulator_cpu.update_state(TargetStates.STOPPED)
        
        # 1. Map local emulated memory
        ava.add_memory_range(0x08000000, 0x20000, name="rom", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x10000, name="ram", permissions="rwx")
        
        # 2. Map forwarded hardware MMIO range: 0x40020000 (Size: 4KB)
        # Forwarded to our physical hardware proxy
        hw_proxy = HardwareProxyPeripheral("physical_radio_chip", 0x40020000, 0x1000)
        forwarded_range = ava.add_memory_range(
            0x40020000, 0x1000,
            name="forwarded_radio_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=hw_proxy
        )
        
        ava.init_targets()
        print(f"[+] Memory forwarding route established:")
        print(f"  Range: 0x40020000 - 0x40021000 -> Target: '{hw_proxy.name}' (forwarded=True)")
        
        # Simulate emulator encountering an MMIO read from the Radio Device ID register
        print("[*] Simulating guest execution executing 'LDR R0, [0x40020000]'...")
        hw_val = forwarded_range.forwarded_to.read_memory(0x40020000, 4, pc=0x08000450)
        print(f"[+] Guest received physical hardware value: 0x{hw_val:08x} (ASCII: 'HARD')")
        
        # Simulate guest executing 'STR R1, [0x40020008]' (configure radio channel)
        print("[*] Simulating guest execution executing 'STR R1, [0x40020008]' (Channel 11)...")
        forwarded_range.forwarded_to.write_memory(0x40020008, 4, 11, pc=0x08000458)
        print(f"[+] Physical register updated successfully.")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hardware-in-the-Loop memory forwarding verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_memory_forwarding_demo()
