# ⚡️ 🎯 Automated Dynamic Breakpoints & Memory Access Watchpoints with Avatar2 Framework (Python practice)
_Post 12/30 · Avatar2 firmware orchestration playbook_

Breakpoints and watchpoints are the primary instruments of dynamic execution control. A breakpoint traps execution when the instruction pointer reaches a designated code address, while a memory watchpoint halts execution whenever data is read from or written to a designated RAM variable or MMIO register.

## 🧠 Core Concept
- `set_breakpoint(address)`: Registering execution traps on subroutine entries or sensitive code branches.
- `set_watchpoint(address, type)`: Registering memory access traps on variables (Read, Write, or Read/Write).
- **Breakpoint Hit Message Processing**: Catching `BreakpointHitMessage` in Avatar's event queues.
- **Contextual Register Snapshotting**: Extracting function arguments (`r0`-`r3`) and call stacks at the moment of impact.
- **Automated Trap Clearence**: Programmatically removing or disabling breakpoints after hits to maintain high throughput.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
ava.add_memory_range(GPIO_BASE, GPIO_SIZE, name="gpio", permissions="rw-")
ava.init_targets()
image = assemble_firmware()
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
instructions = list(md.disasm(image, FLASH_BASE))
```

## 🔥 Use Cases
- Intercepting firmware authentication routines to extract plain PINs, passwords, and tokens.
- Detecting unauthorized writes to critical RTOS scheduler variables and task control blocks.
- Tracing state transitions in embedded Finite State Machines (FSMs).
- Measuring execution time intervals between subroutine entry and return breakpoints.
- Automated crash localization by placing watchpoints on stack canary memory locations.

## ⚠️ Caveats
- Hardware breakpoints on physical Cortex-M chips are limited by hardware FPB units (typically 4 to 6).
- Software breakpoints in Flash ROM require flash patching or FPB hardware remapping.
- Watchpoints monitor aligned 4-byte or 8-byte addresses; unaligned accesses may bypass watchpoint triggers.
- Always remove one-time breakpoints inside your handler to prevent infinite loop re-triggers.

## 📦 Target
- **Target Subroutine**: `auth_verify_pin()` @ `0x080015A0`
- **Target Security Flag**: `g_authenticated` @ `0x20000800`
- **Monitored Registers**: `R0` (Buffer), `R1` (PIN: 1234)

## 🔗 Resources
- Avatar2 Target Breakpoint Interface (https://avatar2.readthedocs.io/en/latest/api/targets.html)
- ARM Cortex-M Flash Patch and Breakpoint (FPB) Unit (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/peripherals/flash-patch-and-breakpoint-unit)
- Hardware vs Software Breakpoint Mechanisms (https://en.wikipedia.org/wiki/Breakpoint)

**Runnable source, run log & report**: [`12_breakpoint_watchpoint_automation`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/12_breakpoint_watchpoint_automation)

#Avatar2 #Breakpoints #Watchpoints #ReverseEngineering #FirmwareSecurity #HardwareHacking
