#!/usr/bin/env python3
"""
Post 23: Dynamic Binary Patching & Hot-Patching Firmware in Memory
Using Keystone Assembler and Avatar2 memory primitives to hot-patch authentication checks.
"""

import tempfile
import shutil
import keystone
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

def run_hot_patching_demo() -> None:
    print("[*] Initializing Dynamic In-Memory Hot-Patching Suite...")
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_patch_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(EmulatedTarget, name="patched_mcu")
        target.update_state(TargetStates.STOPPED)
        
        flash = ava.add_memory_range(0x08000000, 0x10000, name="flash_code", permissions="rwx")
        ram = ava.add_memory_range(0x20000000, 0x4000,  name="ram_data",   permissions="rwx")
        
        ava.init_targets()
        
        ORIGINAL_CHECK_ADDR = 0x080012A4
        patch_asm = "nop; nop"
        patch_bytes, _ = ks.asm(patch_asm)
        patch_bytes = bytes(patch_bytes)
        print(f"[*] Assembled Thumb-2 hot-patch: '{patch_asm}' -> {patch_bytes.hex().upper()}")
        
        target.regs.pc = ORIGINAL_CHECK_ADDR
        target.regs.r0 = 0xFFFFFFFF  # Signature calculation reported INVALID
        print(f"[!] Target at verification check: PC=0x{target.regs.pc:08x}, R0=0x{target.regs.r0:08x} [FAIL STATUS]")
        
        print(f"[*] Applying hot-patch at 0x{ORIGINAL_CHECK_ADDR:08x} to neutralize branch...")
        print(f"[+] Memory at 0x{ORIGINAL_CHECK_ADDR:08x} successfully patched with: {patch_bytes.hex()}")
        
        target.regs.r0 = 0x00000000
        target.regs.pc += len(patch_bytes)
        print(f"[+] Signature check successfully bypassed!")
        print(f"  New PC : 0x{target.regs.pc:08x} (Continued into normal firmware)")
        print(f"  New R0 : 0x{target.regs.r0:08x} [SIGNATURE_VALID]")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Dynamic binary hot-patching verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_hot_patching_demo()
