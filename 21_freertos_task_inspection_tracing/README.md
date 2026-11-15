# ⚡️ 📊 FreeRTOS Kernel Data Structure Introspection & Task Tracing with Avatar2 Framework (Python practice)
_Post 21/30 · Avatar2 firmware orchestration playbook_

FreeRTOS is the most widely deployed real-time operating system for embedded microcontrollers. Unlike bare-metal 'superloops', FreeRTOS schedules execution across multiple preemptible tasks, each with its own private stack and Task Control Block (TCB).

## 🧠 Core Concept
- **TCB Architecture**: Structure of FreeRTOS `tskTaskControlBlock` (stack pointers, state list items, task names).
- `pxCurrentTCB` Pointer Resolution: Reading the kernel's active task pointer from internal SRAM.
- **Ready List Walking**: Traversing circular doubly-linked lists (`List_t`) to enumerate all running tasks.
- **Stack Overflow Detection**: Checking the stack watermark marker bytes (`0xA5A5A5A5`) at the top of task stacks.
- **Context Switch Tracing**: Hooking the `PendSV` interrupt or scheduler to log task preemption events.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="freertos_core")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(0x08000000, 0x20000, name="rtos_flash", permissions="r-x")
ava.add_memory_range(0x20000000, 0x10000, name="rtos_sram", permissions="rwx")
ava.init_targets()
introspector = FreeRTOSIntrospector(target)
introspector.add_simulated_tcb(0x20001000, "IDLE", 0, 0x200013E0, 0x20001000)
introspector.add_simulated_tcb(0x20001400, "NetworkTask", 3, 0x200017D0, 0x20001400)
introspector.add_simulated_tcb(0x20001800, "CryptoEngine", 2, 0x20001BD8, 0x20001800)
```

## 🔥 Use Cases
- Detecting stack overflow vulnerabilities in high-priority network and parser tasks.
- Forensic identification of active FreeRTOS tasks during unhandled HardFault exceptions.
- Tracing context switch latency and priority inversion in safety-critical automotive systems.
- Extracting private per-task encryption keys stored on task stacks.
- Auditing FreeRTOS dynamic memory heap allocators (`heap_4.c` / `heap_5.c`) for fragmentation.

## ⚠️ Caveats
- FreeRTOS struct field offsets vary based on compile-time configuration macros in `FreeRTOSConfig.h`.
- If `configUSE_TRACE_FACILITY` or `configUSE_STATS_FORMATTING_FUNCTIONS` are disabled, names may be stripped.
- Reading live TCBs while the target CPU is actively executing causes race conditions; always halt the target first.
- Stack growth direction on ARM Cortex-M is downward; stack headroom is `(SP - StackBase)`.

## 📦 Target
- **RTOS Kernel**: FreeRTOS Kernel v10.x
- **Target Tasks**: `IDLE` (Prio 0), `NetworkTask` (Prio 3), `CryptoEngine` (Prio 2), `SensorsTask` (Prio 1)
- **TCB Base**: `0x20001000`

## 🔗 Resources
- FreeRTOS Kernel Internal Data Structures (https://www.freertos.org/a00017.html)
- Mastering the FreeRTOS Real Time Kernel (https://www.freertos.org/Documentation/RTOS_book.html)
- Avatar2 State Introspection (https://avatar2.readthedocs.io/en/latest/)

**Runnable source, run log & report**: [`21_freertos_task_inspection_tracing`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/21_freertos_task_inspection_tracing)

#Avatar2 #FreeRTOS #RTOS #FirmwareSecurity #EmbeddedSystems #ReverseEngineering
