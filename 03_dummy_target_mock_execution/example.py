#!/usr/bin/env python3
"""
Post 03: Mock Target Orchestration and Unit-Testing without Physical Hardware
Using DummyTarget with register emulation to test calling conventions in unit tests.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._regs = {}
    def read_register(self, reg):
        return self._regs.get(reg, 0)
    def write_register(self, reg, val):
        self._regs[reg] = val
        return True

def run_dummy_target_demo() -> None:
    print("[*] Initializing DummyTarget for Synthetic Unit-Testing...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_dummy_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(EmulatedTarget, name="mock_cortex_m3")
        target.update_state(TargetStates.STOPPED)
        
        ava.init_targets()
        print(f"[+] DummyTarget '{target.name}' initialized in state: {target.state}")
        
        # Simulate initial reset vector state
        print("[*] Setting initial CPU register state (ARM Cortex-M reset)...")
        target.regs.sp = 0x20010000   # Initial Stack Pointer (top of SRAM)
        target.regs.pc = 0x08000101   # Reset Handler address (Thumb mode)
        target.regs.lr = 0xFFFFFFFF   # EXC_RETURN initial value
        
        # Simulate calling a cryptographic hashing function: hash_payload(data_ptr, length)
        # Arguments passed in r0 and r1 according to AAPCS
        target.regs.r0 = 0x20001000   # Arg 0: pointer to payload buffer
        target.regs.r1 = 256          # Arg 1: buffer size in bytes
        
        print(f"[+] Register Context:")
        print(f"  SP : 0x{target.regs.sp:08x}  LR : 0x{target.regs.lr:08x}")
        print(f"  PC : 0x{target.regs.pc:08x}  R0 : 0x{target.regs.r0:08x} (Buffer: 0x{target.regs.r0:08x})")
        print(f"  R1 : {target.regs.r1} bytes")
        
        # Simulate function execution completing and returning status code
        target.regs.r0 = 0x00000000   # Return code 0 (SUCCESS)
        print(f"[+] Function return value (R0): {target.regs.r0} [SUCCESS]")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] DummyTarget test workflow completed cleanly.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_dummy_target_demo()
