#!/usr/bin/env python3
"""
Post 01: Avatar2 Core Orchestrator Initialization & Architecture Lifecycle
Initializes the central Avatar orchestrator, inspects target containers, and executes clean shutdown.
"""

import os
import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

def run_orchestrator_demo() -> None:
    print("[*] Initializing Avatar2 Core Orchestrator...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_ws_")
    try:
        # Initialize Avatar with ARM Cortex-M3 architecture specification
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        print(f"[+] Workspace created   : {os.path.basename(workspace_dir)}")
        print(f"[+] Target architecture   : {ava.arch.__class__.__name__}")
        
        # Register an execution target into the orchestrator
        print("[*] Registering target 'cortex_m3_cpu' (DummyTarget)...")
        target = ava.add_target(DummyTarget, name="cortex_m3_cpu")
        target.update_state(TargetStates.STOPPED)
        
        # Initialize registered targets
        ava.init_targets()
        print(f"[+] Target '{target.name}' initialized. Current state: {target.state}")
        
        # Inspect target properties
        print(f"[+] Registered targets count: {len(ava.targets)}")
        print(f"[+] Active memory ranges    : {len(ava.memory_ranges)}")
        
        # Clean teardown
        print("[*] Performing graceful orchestrator shutdown...")
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Orchestrator lifecycle completed cleanly.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_orchestrator_demo()
