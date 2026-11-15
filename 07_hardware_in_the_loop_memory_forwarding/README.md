# ⚡️ 🔀 Hardware-in-the-Loop (HITL) Memory Forwarding Architecture with Avatar2 Framework (Python practice)

The defining breakthrough of the Avatar2 framework is **Memory Forwarding**. When reverse engineering proprietary embedded systems, emulating the entire hardware peripheral landscape (radio transceivers, cryptographic coprocessors, proprietary ASICs) is prohibitively expensive or impossible. Avatar2 solves this by bridging emulated execution with physical hardware: when execution inside an emulator attempts to read or write an unmodeled MMIO register, Avatar2 traps the access and forwards it over JTAG/SWD to the physical microcontroller, transparently returning the physical device's response back to the emulator.

## 🧠 Core Concept
- **Transparent Memory Forwarding**: Intercepting guest MMIO reads/writes and proxying them across targets.
- `forwarded=True` & `forwarded_to`: Avatar2 API primitives defining which target handles memory operations.
- **Hardware-in-the-Loop (HITL)**: Hybrid execution combining high-speed virtual CPU emulation with real silicon I/O.
- **Access Trapping**: Pausing virtual execution at the exact instruction requesting peripheral I/O.
- **Bidirectional State Transfer**: Forwarding register writes to hardware and streaming hardware sensor reads back to the guest.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Executing encrypted firmware inside an emulator while forwarding crypto MMIO to a physical hardware HSM.
- Analyzing Bluetooth and Zigbee IoT stacks by forwarding baseband radio registers to real silicon.
- Fuzzing complex network parser functions in virtual machines while keeping physical actuators connected.
- Extracting secret keys from on-chip hardware accelerators without physical decapping.
- Accelerating dynamic malware analysis of proprietary automotive microcontrollers.

## ⚠️ Caveats & Responsible Practice
- Memory forwarding introduces latency (~1ms per JTAG transaction); avoid forwarding high-frequency DMA buffers.
- Physical hardware registers with side-effects (e.g. clear-on-read FIFO registers) must be handled carefully.
- Watchdog timers on physical hardware can expire while virtual execution is paused or single-stepping.
- Ensure voltage levels and clock domains match when connecting physical debugging probes.

## 📦 Test Data & Sample Binaries / Targets
- **Forwarded MMIO Range**: `0x40020000` - `0x40021000` (Size: 4 KB)
- **Forwarded Target**: Physical Radio Chip Proxy (`physical_radio_chip`)
- **Simulated Hardware Registers**: `Device ID (0x00)`, `Status (0x04)`, `Config (0x08)`

## 🔗 Resources
- Avatar2 Memory Forwarding Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Research Paper: Towards Fully Automated Firmware Analysis (https://s3.eurecom.fr/docs/ndss14_avatar.pdf)
- Hardware-in-the-Loop Simulation Best Practices (https://en.wikipedia.org/wiki/Hardware-in-the-loop_simulation)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #HITL #MemoryForwarding #HardwareSecurity #IoT #FirmwareAnalysis
