#!/usr/bin/env python3
"""
Post 02: Granular Address Space Configuration & Memory Range Protection
Configuring Flash, SRAM, and MMIO memory ranges with permission controls and interval trees.
"""

import os
import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

def run_memory_layout_demo() -> None:
    print("[*] Configuring Avatar2 Granular Memory Space...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_mem_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="mcu_core")
        
        # 1. Map Flash Memory (Internal ROM): 0x08000000 - 512KB (r-x)
        flash = ava.add_memory_range(
            0x08000000, 0x80000, name="internal_flash", permissions="r-x"
        )
        
        # 2. Map SRAM Memory (Data / Stack): 0x20000000 - 128KB (rwx)
        sram = ava.add_memory_range(
            0x20000000, 0x20000, name="internal_sram", permissions="rwx"
        )
        
        # 3. Map Peripheral MMIO Region: 0x40000000 - 64KB (rw-)
        mmio = ava.add_memory_range(
            0x40000000, 0x10000, name="peripheral_mmio", permissions="rw-"
        )
        
        target.update_state(TargetStates.STOPPED)
        ava.init_targets()
        
        print(f"[+] Configured {len(ava.memory_ranges)} discrete memory ranges:")
        for interval in ava.memory_ranges:
            mr = interval.data
            print(f"  -> {mr.name:<18} [0x{mr.address:08x} - 0x{mr.address + mr.size:08x}] Perms: {mr.permissions} (Size: {mr.size // 1024} KB)")
            
        # Query interval tree for address lookup
        test_addr = 0x20004500
        match = ava.memory_ranges.at(test_addr)
        if match:
            matched_mr = next(iter(match)).data
            print(f"[+] Address 0x{test_addr:08x} resolved to region: '{matched_mr.name}'")
            
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Memory mapping verified successfully.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_memory_layout_demo()
