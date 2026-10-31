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
