# ⚡️ 🛡 Embedded Anti-Debugging Detection & Neutralization (Python practice)

High-security embedded firmware (automotive gateways, IoT payment terminals, smart meters) frequently incorporates anti-debugging checks to thwart reverse engineering.

## 🧠 Core Concept
- **Cortex-M CoreDebug Registers**: Inspecting `DHCSR` (Debug Halting Control and Status Register @ `0xE000EDF0`).
- **`C_DEBUGEN` Bit Spoofing**: Returning 0 on `DHCSR` reads so firmware believes no debugger is attached.
- **DWT Cycle Counter Neutralization**: Defeating time-delta checks measuring execution delays between instructions.
- **DBGMCU Configuration Virtualization**: Masking debug freeze control bits in microcontroller system registers.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 26: Embedded Anti-Debugging Detection & Neutralization.
Neutralizes ARM CoreDebug DHCSR queries and DWT cycle-counter timing checks in Avatar2."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

SCS_BASE, SCS_SIZE, DHCSR, DWT_CYCCNT = 0xE000E000, 0x1000, 0xEDF0, 0xE004


class StealthCoreDebugBlock(AvatarPeripheral):
    """C_DEBUGEN always reads 0; CYCCNT advances slowly enough to beat the delta check."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.cycles = 0

    def read(self, offset, size):
        if offset == DHCSR:                          # 'no debugger attached'
            print("[STEALTH] DHCSR -> 0x00000000 (C_DEBUGEN=0)")
            return 0
        if offset == DWT_CYCCNT:                     # plausible, non-emulator timing
            self.cycles += 1
            return self.cycles
        return 0


def run_anti_debug_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="tamper_core")
    target.update_state(TargetStates.STOPPED)
    scs = StealthCoreDebugBlock("core_debug", SCS_BASE, SCS_SIZE)
    route = ava.add_memory_range(SCS_BASE, SCS_SIZE, name="scs_mmio",
                                 permissions="rw-", forwarded=True, forwarded_to=scs)
    ava.init_targets()

    assert (route.forwarded_to.read(DHCSR, 4) & 1) == 0
    print("[+] check bypassed: firmware believes no debugger is attached")
    first = route.forwarded_to.read(DWT_CYCCNT, 4)
    second = route.forwarded_to.read(DWT_CYCCNT, 4)
    print(f"[+] CYCCNT delta={second - first} (under the 1000-cycle threshold)")
    ava.shutdown()


if __name__ == "__main__":
    run_anti_debug_demo()
```

## 🔥 Use Cases
- Bypassing anti-tamper wipe mechanisms in banking terminals and Point-of-Sale (POS) devices.
- Neutralizing DWT cycle timing checks in game console security microcontrollers.
- Conducting undisturbed dynamic analysis of obfuscated IoT malware.
- Analyzing automotive electronic keys without triggering anti-cloning lockouts.

## ⚠️ Caveats & Responsible Practice
- Some microcontrollers use proprietary vendor registers (such as STM32 `DBGMCU_CR`) in addition to standard ARM SCS.
- Single-stepping code that reads the SysTick current value (`STK_CVR`) can also reveal debugger presence.
- External watchdogs or companion monitoring chips can detect halted CPU cores independently.

## 📦 Test Data & Sample Binaries
- **Target Register**: ARM CoreDebug DHCSR @ `0xE000EDF0`
- **Target Timing Unit**: DWT Cycle Counter (`DWT_CYCCNT`)
- **Spoofed Values**: `DHCSR = 0x00000000`, `Delta = 5 cycles`

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #AntiDebug #CoreDebug #HardwareSecurity #ReverseEngineering #FirmwareSecurity
