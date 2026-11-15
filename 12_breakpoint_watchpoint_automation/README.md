# ⚡️ 🎯 Automated Dynamic Breakpoints & Memory Access Watchpoints (Python practice)

Breakpoints and watchpoints are the primary instruments of dynamic execution control.

## 🧠 Core Concept
- `set_breakpoint(address)`: Registering execution traps on subroutine entries or sensitive code branches.
- `set_watchpoint(address, type)`: Registering memory access traps on variables (Read, Write, or Read/Write).
- **Breakpoint Hit Message Processing**: Catching `BreakpointHitMessage` in Avatar's event queues.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 12: Automated Dynamic Breakpoints & Memory Access Watchpoints.
Real execution breakpoints and data watchpoints on a live Cortex-M3 firmware loop."""

import capstone
import keystone
import unicorn

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, RAM_BASE, MEM_SIZE, COUNTER = 0x08000000, 0x20000000, 0x1000, 0x20000000


def run_breakpoint_watchpoint_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
    ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
    ava.init_targets()

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    image, _ = ks.asm("ldr r4, =0x20000000\nmovs r0, #0\n"
                      "loop: adds r0, r0, #1\nstr r0, [r4]\nb loop")
    insns = list(capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
                 .disasm(bytes(image), FLASH_BASE))
    store = next(i.address for i in insns if i.mnemonic == "str")
    loop = next(i.address for i in insns if i.mnemonic == "adds")
    print(f"[+] breakpoint 0x{store:08x} | watchpoint 0x{COUNTER:08x}")

    uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                    ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
    uc.mem_map(FLASH_BASE, MEM_SIZE)
    uc.mem_map(RAM_BASE, MEM_SIZE)
    uc.mem_write(FLASH_BASE, bytes(image))
    hits = {"bp": 0, "wp": 0}

    def watchpoint(_uc, access, address, size, value, _user):
        hits["wp"] += 1
        print(f"[WATCHPOINT] write {value} -> 0x{address:08x}")

    def breakpoint(handle, address, size, _user):
        hits["bp"] += 1
        print(f"[BREAKPOINT] PC=0x{address:08x} R0={handle.reg_read(0)}")

    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, watchpoint, begin=COUNTER, end=COUNTER + 3)
    uc.hook_add(unicorn.UC_HOOK_CODE, breakpoint, begin=store, end=store + 3)
    uc.emu_start(loop | 1, 0, count=200)
    print(f"[+] hits={hits['bp']} watchpoint_writes={hits['wp']}")
    ava.shutdown()


if __name__ == "__main__":
    run_breakpoint_watchpoint_demo()
```

## 🔥 Use Cases
- Intercepting firmware authentication routines to extract plain PINs, passwords, and tokens.
- Detecting unauthorized writes to critical RTOS scheduler variables and task control blocks.
- Tracing state transitions in embedded Finite State Machines (FSMs).

## ⚠️ Caveats & Responsible Practice
- Hardware breakpoints on physical Cortex-M chips are limited by hardware FPB units (typically 4 to 6).
- Software breakpoints in Flash ROM require flash patching or FPB hardware remapping.

## 📦 Test Data & Sample Binaries
- **Target Subroutine**: `auth_verify_pin()` @ `0x080015A0`
- **Target Security Flag**: `g_authenticated` @ `0x20000800`
- **Monitored Registers**: `R0` (Buffer), `R1` (PIN: 1234)

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #Breakpoints #Watchpoints #ReverseEngineering #FirmwareSecurity #HardwareHacking
