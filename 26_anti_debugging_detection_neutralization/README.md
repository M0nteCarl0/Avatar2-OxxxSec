# ⚡️ 🛡 Embedded Anti-Debugging Detection & Neutralization with Avatar2 Framework (Python practice)

High-security embedded firmware (automotive gateways, IoT payment terminals, smart meters) frequently incorporates anti-debugging checks to thwart reverse engineering. Microcontrollers provide hardware registers that reveal when a debugger is attached: the ARM Cortex-M `CoreDebug->DHCSR` register has a `C_DEBUGEN` bit asserted by hardware when JTAG/SWD probes are connected, while Data Watchpoint and Trace (DWT) cycle counters detect timing delays caused by single-stepping. Avatar2 allows researchers to intercept reads from these hardware debug registers, spoof benign responses, and render the debugger completely invisible to the guest firmware.

## 🧠 Core Concept
- **Cortex-M CoreDebug Registers**: Inspecting `DHCSR` (Debug Halting Control and Status Register @ `0xE000EDF0`).
- **`C_DEBUGEN` Bit Spoofing**: Returning 0 on `DHCSR` reads so firmware believes no debugger is attached.
- **DWT Cycle Counter Neutralization**: Defeating time-delta checks measuring execution delays between instructions.
- **DBGMCU Configuration Virtualization**: Masking debug freeze control bits in microcontroller system registers.
- **Transparent Stealth Execution**: Maintaining full dynamic instrumentation control without triggering anti-tamper resets.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 26: Embedded Anti-Debugging Detection & Neutralization
Neutralizing ARM CoreDebug DHCSR queries and DWT cycle counter timing checks in Avatar2.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class StealthCoreDebugBlock(AvatarPeripheral):
    """
    Simulates ARMv7-M System Control Space (SCS) & CoreDebug Block.
    Base: 0xE000ED00 (Size: 4KB)
    Registers:
      0xDF0: DHCSR (Debug Halting Control and Status Register)
             Bit 0: C_DEBUGEN (1 if debugger attached, 0 if standalone)
      0x1004: DWT_CYCCNT (Cycle Count Register)
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0xDF0:0xDF4] = self.read_dhcsr
        self.read_handler[0x004:0x008] = self.read_dwt_cyccnt
        self.spoofed_cycle_count = 1000

    def read_dhcsr(self, offset, size, pc=0):
        # When physical JTAG is connected, hardware sets C_DEBUGEN (0x00000001).
        # Firmware checks: if (CoreDebug->DHCSR & CoreDebug_DHCSR_C_DEBUGEN_Msk) trigger_tamper();
        # We spoof return value to 0x00000000 (STEALTH MODE)!
        print(f"[ANTI-DEBUG TRAP] PC 0x{pc:08x} read CoreDebug->DHCSR! Spoofing C_DEBUGEN = 0 (Debugger Hidden)")
        return 0x00000000

    def read_dwt_cyccnt(self, offset, size, pc=0):
        # Firmware measures elapsed cycles between two points to detect single-stepping.
        # We return deterministic small increments to defeat timing checks.
        self.spoofed_cycle_count += 5
        print(f"[ANTI-DEBUG TIMING] PC 0x{pc:08x} read DWT_CYCCNT! Returning spoofed cycles: {self.spoofed_cycle_count}")
        return self.spoofed_cycle_count

def run_anti_debug_demo() -> None:
    print("[*] Initializing Embedded Anti-Debugging Neutralization Harness...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_antidebug_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="tamper_core")
        target.update_state(TargetStates.STOPPED)
        
        # Map System Control Space (SCS) at 0xE000E000
        scs_block = StealthCoreDebugBlock("core_debug", 0xE000E000, 0x1000)
        mr = ava.add_memory_range(
            0xE000E000, 0x1000,
            name="scs_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=scs_block
        )
        
        ava.init_targets()
        print(f"[+] Stealth CoreDebug block mapped at 0xE000E000.")
        
        # 1. Simulate firmware executing anti-debug check:
        # LDR R0, =0xE000EDF0 (DHCSR)
        # LDR R1, [R0]
        # TST R1, #1 ; Test C_DEBUGEN
        print("[*] Simulating firmware executing 'check_debugger_present()'...")
        dhcsr_val = mr.forwarded_to.read_memory(0xE000EDF0, 4, pc=0x08000550)
        print(f"[+] Firmware received DHCSR: 0x{dhcsr_val:08x} (C_DEBUGEN bit is 0)")
        assert (dhcsr_val & 1) == 0
        print("[+] Anti-debug check bypassed: Firmware concluded 'NO DEBUGGER CONNECTED'!")
        
        # 2. Simulate firmware measuring timing delta with DWT cycle counter
        print("[*] Simulating firmware checking DWT execution cycle delta...")
        t1 = mr.forwarded_to.read_memory(0xE000E004, 4, pc=0x08000560)
        t2 = mr.forwarded_to.read_memory(0xE000E004, 4, pc=0x08000568)
        delta = t2 - t1
        print(f"[+] Measured cycle delta: {delta} cycles (Normal execution speed, no stepping detected)")
        assert delta == 5
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Anti-debugging detection and neutralization verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_anti_debug_demo()
```

## 🔥 Use Cases
- Bypassing anti-tamper wipe mechanisms in banking terminals and Point-of-Sale (POS) devices.
- Neutralizing DWT cycle timing checks in game console security microcontrollers.
- Conducting undisturbed dynamic analysis of obfuscated IoT malware.
- Analyzing automotive electronic keys without triggering anti-cloning lockouts.
- Auditing device firmware for compliance with secure development guidelines.

## ⚠️ Caveats & Responsible Practice
- Some microcontrollers use proprietary vendor registers (such as STM32 `DBGMCU_CR`) in addition to standard ARM SCS.
- Single-stepping code that reads the SysTick current value (`STK_CVR`) can also reveal debugger presence.
- External watchdogs or companion monitoring chips can detect halted CPU cores independently.
- Ensure the System Control Space is mapped with appropriate permissions (`rw-`).

## 📦 Test Data & Sample Binaries / Targets
- **Target Register**: ARM CoreDebug DHCSR @ `0xE000EDF0`
- **Target Timing Unit**: DWT Cycle Counter (`DWT_CYCCNT`)
- **Spoofed Values**: `DHCSR = 0x00000000`, `Delta = 5 cycles`

## 🔗 Resources
- ARM Cortex-M3 CoreDebug Registers Specification (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/peripherals/coredebug)
- Anti-Debugging Techniques in Embedded ARM Firmware (https://www.blackhat.com/docs/us-15/materials/us-15-Colley-Hacking-Hardware-With-Software.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #AntiDebug #CoreDebug #HardwareSecurity #ReverseEngineering #FirmwareSecurity
