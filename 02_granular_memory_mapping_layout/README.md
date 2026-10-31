# ⚡️ 🗺 Granular Address Space Configuration & Memory Range Protection with Avatar2 Framework (Python practice)

Embedded microcontrollers do not have unified flat memory spaces like typical desktop processes. Instead, their address space is strictly segmented into non-contiguous hardware regions: Flash ROM, internal SRAM, external memory banks, and memory-mapped I/O (MMIO) peripheral blocks. Avatar2 implements an interval-tree-backed memory management engine that allows security researchers to construct granular memory maps with explicit permission bitmasks (`rwx`), file-backed storage, and overlap protection.

## 🧠 Core Concept
- **IntervalTree Memory Management**: High-speed O(log N) lookup of memory ranges based on target physical addresses.
- **Access Permissions Enforcement**: Granular configuration of Read (`r`), Write (`w`), and Execute (`x`) attributes.
- **Region Classification**: Categorizing address blocks into ROM (Flash), RAM (SRAM/DRAM), and MMIO peripheral banks.
- **Overlap Detection**: Safeguards preventing conflicting memory allocations across orchestrated targets.
- **Query & Resolution API**: Resolving guest memory addresses to concrete memory ranges and metadata at runtime.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Replicating exact datasheet memory maps for STM32, NXP, ESP32, and Nordic microcontrollers.
- Enforcing W^X (Write XOR Execute) security policies to detect buffer overflow exploit payloads.
- Detecting unmapped null-pointer dereferences in embedded bootloaders.
- Mapping non-contiguous external flash banks (SPI NOR Flash) at high memory offsets.
- Automated sanity-checking of linker script (`.ld`) section outputs against virtual layouts.

## ⚠️ Caveats & Responsible Practice
- Ensure range boundaries match hardware page alignment (typically 1KB or 4KB boundaries).
- Marking MMIO regions as executable (`rwx`) can mask instruction fetch vulnerabilities.
- Overlapping memory intervals will raise exceptions unless explicitly configured.
- Memory range permissions must be respected by the underlying target execution engine.

## 📦 Test Data & Sample Binaries / Targets
- **Flash Base**: `0x08000000` (Size: 512 KB, Permissions: `r-x`)
- **SRAM Base**: `0x20000000` (Size: 128 KB, Permissions: `rwx`)
- **MMIO Base**: `0x40000000` (Size: 64 KB, Permissions: `rw-`)

## 🔗 Resources
- Avatar2 Memory Management Architecture (https://avatar2.readthedocs.io/en/latest/api/memory.html)
- ARM Cortex-M Memory Model Documentation (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/memory-model)
- IntervalTree Python Library Documentation (https://pypi.org/project/intervaltree/)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #MemoryMapping #FirmwareSecurity #EmbeddedSystems #ARM #ReverseEngineering
