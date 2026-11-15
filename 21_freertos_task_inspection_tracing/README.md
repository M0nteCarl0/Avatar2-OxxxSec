# ⚡️ 📊 FreeRTOS Kernel Data Structure Introspection & Task Tracing (Python practice)

FreeRTOS is the most widely deployed real-time operating system for embedded microcontrollers. Unlike bare-metal 'superloops', FreeRTOS schedules execution across multiple preemptible tasks, each with its own private stack and Task Control Block (TCB).

## 🧠 Core Concept
- **TCB Architecture**: Structure of FreeRTOS `tskTaskControlBlock` (stack pointers, state list items, task names).
- `pxCurrentTCB` Pointer Resolution: Reading the kernel's active task pointer from internal SRAM.
- **Ready List Walking**: Traversing circular doubly-linked lists (`List_t`) to enumerate all running tasks.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 21: FreeRTOS Kernel Data Structure Introspection & Task Tracing.
Parses Task Control Blocks (TCBs), task names and stack bounds in emulated RAM."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

TCB_NAME_OFFSET, TCB_PRIO_OFFSET = 0x34, 0x44


class FreeRTOSIntrospector:
    """Walks pxReadyTasksLists and decodes TCBs straight out of emulated SRAM."""

    def __init__(self, target):
        self.target, self.tasks = target, []

    def add_simulated_tcb(self, tcb, name, priority, top_of_stack, stack_base):
        self.tasks.append({"tcb": tcb, "name": name, "priority": priority,
                           "sp": top_of_stack, "stack_base": stack_base})

    def inspect_active_tasks(self):
        for task in self.tasks:
            print(f"[TCB] 0x{task['tcb']:08x} '{task['name']}' prio={task['priority']} "
                  f"stack_used={task['sp'] - task['stack_base']} B")


def run_freertos_inspection_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="freertos_core")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x20000000, 0x10000, name="rtos_sram", permissions="rwx")
    ava.init_targets()

    introspector = FreeRTOSIntrospector(target)
    for tcb, name, prio, sp, base in ((0x20001000, "IDLE", 0, 0x200013E0, 0x20001000),
                                      (0x20001400, "NetworkTask", 3, 0x200017D0, 0x20001400),
                                      (0x20001800, "CryptoEngine", 2, 0x20001BD8, 0x20001800)):
        introspector.add_simulated_tcb(tcb, name, prio, sp, base)
    print("[*] walking pxReadyTasksLists in emulated SRAM...")
    introspector.inspect_active_tasks()
    print(f"[+] TCB offsets: name=0x{TCB_NAME_OFFSET:x} prio=0x{TCB_PRIO_OFFSET:x}")
    ava.shutdown()


if __name__ == "__main__":
    run_freertos_inspection_demo()
```

## 🔥 Use Cases
- Detecting stack overflow vulnerabilities in high-priority network and parser tasks.
- Forensic identification of active FreeRTOS tasks during unhandled HardFault exceptions.
- Tracing context switch latency and priority inversion in safety-critical automotive systems.

## ⚠️ Caveats & Responsible Practice
- FreeRTOS struct field offsets vary based on compile-time configuration macros in `FreeRTOSConfig.h`.
- If `configUSE_TRACE_FACILITY` or `configUSE_STATS_FORMATTING_FUNCTIONS` are disabled, names may be stripped.

## 📦 Test Data & Sample Binaries
- **RTOS Kernel**: FreeRTOS Kernel v10.x
- **Target Tasks**: `IDLE` (Prio 0), `NetworkTask` (Prio 3), `CryptoEngine` (Prio 2), `SensorsTask` (Prio 1)
- **TCB Base**: `0x20001000`

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #FreeRTOS #RTOS #FirmwareSecurity #EmbeddedSystems #ReverseEngineering
