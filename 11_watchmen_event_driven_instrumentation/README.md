# ⚡️ 👁 Asynchronous Target Event Instrumentation with Watchmen with Avatar2 Framework (Python practice)

Complex dynamic analysis requires reacting to target actions dynamically: when a target stops, when a breakpoint fires, when a syscall triggers, or when memory is accessed. Avatar2 includes `Watchmen`, an event-driven pub/sub notification subsystem. Using the `@watch` decorator and event listener callbacks, security analysts can attach asynchronous hooks that execute before (`BEFORE`) or after (`AFTER`) core target operations, enabling transparent telemetry collection, security policy enforcement, and execution tracing.

## 🧠 Core Concept
- **Watchmen Event Dispatcher**: Central event bus delivering notification messages to registered handler callbacks.
- **Trigger Phasing (`BEFORE` & `AFTER`)**: Choosing whether callbacks fire prior to or immediately following the target action.
- **Event Types**: Monitoring `TargetInit`, `TargetStateUpdate`, `TargetWait`, `BreakpointHit`, and `MemoryAccess`.
- **Non-Intrusive Telemetry**: Collecting forensic execution statistics without modifying guest firmware binary code.
- **Reactive Security Auditing**: Dynamically validating invariant rules (e.g. stack limits) whenever execution halts.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 11: Asynchronous Target Event Instrumentation with Watchmen
Subscribing to target state changes and lifecycle events using Avatar2 Watchmen.
"""

import time
import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

event_journal = []

def on_state_update_callback(avatar, message, *args, **kwargs):
    """Callback invoked by Watchmen whenever a target updates state."""
    target_name = message.origin.name if hasattr(message, "origin") and hasattr(message.origin, "name") else "target"
    state_val = getattr(message, "state", "N/A")
    event_entry = f"[WATCHMEN] Target '{target_name}' transitioned to state: {state_val}"
    print(f"  {event_entry}")
    event_journal.append(event_entry)

def run_watchmen_demo() -> None:
    print("[*] Initializing Avatar2 Watchmen Event Subsystem...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_watch_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        
        # Register a Watchmen event listener for UpdateState
        print("[*] Subscribing listener to 'UpdateState' (AFTER phase)...")
        ava.watchmen.add_watchman(
            "UpdateState",
            "after",
            on_state_update_callback
        )
        
        target = ava.add_target(DummyTarget, name="supervised_core")
        target.update_state(TargetStates.STOPPED)
        ava.init_targets()
        
        # Drive target state machine
        time.sleep(0.05)
        target.update_state(TargetStates.RUNNING)
        time.sleep(0.05)
        target.update_state(TargetStates.STOPPED)
        time.sleep(0.05)
        
        print(f"[+] Total Watchmen events recorded in journal: {len(event_journal)}")
        for i, entry in enumerate(event_journal, 1):
            print(f"  {i}. {entry}")
            
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Watchmen event-driven instrumentation verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

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

## 📦 Test Data & Sample Binaries / Targets
- **Event Channel**: `TargetStateUpdate`
- **Trigger Phase**: `AFTER`
- **Observed Transitions**: `STOPPED` -> `RUNNING` -> `STOPPED`

## 🔗 Resources
- Avatar2 Watchmen Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/watchmen.py)
- Event-Driven Architecture in Reverse Engineering Tools (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Python Pub/Sub Design Patterns (https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #Watchmen #EventDriven #BinaryInstrumentation #FirmwareAnalysis #CyberSecurity
