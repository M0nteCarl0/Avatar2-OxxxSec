# ⚡️ 👁 Asynchronous Target Event Instrumentation with Watchmen (Python practice)

Complex dynamic analysis requires reacting to target actions dynamically: when a target stops, when a breakpoint fires, when a syscall triggers, or when memory is accessed. Avatar2 includes `Watchmen`, an event-driven pub/sub notification subsystem.

## 🧠 Core Concept
- **Watchmen Event Dispatcher**: Central event bus delivering notification messages to registered handler callbacks.
- **Trigger Phasing (`BEFORE` & `AFTER`)**: Choosing whether callbacks fire prior to or immediately following the target action.
- **Event Types**: Monitoring `TargetInit`, `TargetStateUpdate`, `TargetWait`, `BreakpointHit`, and `MemoryAccess`.
- **Non-Intrusive Telemetry**: Collecting forensic execution statistics without modifying guest firmware binary code.
- **Reactive Security Auditing**: Dynamically validating invariant rules (e.g. stack limits) whenever execution halts.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 11: Asynchronous Target Event Instrumentation with Watchmen.
Subscribes to target state changes and lifecycle events using Avatar2 Watchmen."""

import time

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

event_journal = []


def on_state_update_callback(message):
    """Watchman callback: fires whenever any target publishes UpdateState."""
    origin = getattr(getattr(message, "origin", None), "name", "target")
    entry = f"[WATCHMEN] '{origin}' -> {getattr(message, 'state', 'N/A')}"
    event_journal.append(entry)
    print(f"  {entry}")


def run_watchmen_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    ava.watchmen.add_watchman("UpdateState", "after", on_state_update_callback)
    target = ava.add_target(DummyTarget, name="supervised_core")
    target.update_state(TargetStates.STOPPED)
    ava.init_targets()
    for state in (TargetStates.RUNNING, TargetStates.STOPPED):
        target.update_state(state)
        time.sleep(0.05)
    print(f"[+] events recorded: {len(event_journal)}")
    ava.stop()
    ava.fast_queue_listener.stop()
    ava.shutdown()


if __name__ == "__main__":
    run_watchmen_demo()
```

## 🔥 Use Cases
- Automated logging of target state transitions during long-running firmware fuzzing runs.
- Enforcing execution timeouts and watchdog policies when targets enter unhandled states.
- Capturing instruction trace logs automatically whenever a target enters `TargetStates.STOPPED`.
- Building live terminal dashboards displaying multi-target cluster status in real time.
- Synchronizing external network traffic packet sniffers to target execution milestones.

## ⚠️ Caveats & Responsible Practice
- Watchmen callbacks run synchronously within event dispatcher threads; avoid heavy I/O operations inside hooks.
- Exceptions raised inside callbacks can disrupt the internal message processing pipeline.
- Use `AFTER` callbacks when inspecting updated register values to ensure the target state has finalized.
- Be aware of thread safety when accessing shared data structures from multiple Watchmen callbacks.

## 📦 Test Data & Sample Binaries
- **Event Channel**: `TargetStateUpdate`
- **Trigger Phase**: `AFTER`
- **Observed Transitions**: `STOPPED` -> `RUNNING` -> `STOPPED`

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #Watchmen #EventDriven #BinaryInstrumentation #FirmwareAnalysis #CyberSecurity
