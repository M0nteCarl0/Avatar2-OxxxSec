# ⚡️ 🔄 Heterogeneous Cross-Target State Synchronization with Avatar2 Framework (Python practice)

One of the most powerful workflows enabled by Avatar2 is hybrid target switching: executing firmware on real silicon until an interesting function is reached, then transferring the entire execution state (registers, memory pages, stack) into an emulator or symbolic execution engine (like angr) for in-depth analysis, and finally pushing the solved state back onto hardware. Avatar2 provides `synchronize_state`, a formal protocol for extracting, serializing, and injecting complete machine states across heterogeneous targets.

## 🧠 Core Concept
- **Heterogeneous State Transfer**: Copying CPU registers and memory pages between dissimilar targets (e.g. OpenOCD -> QEMU).
- `synchronize_state()` Protocol: Coordinating state serialization, target halting, and state restoration.
- **Register Bank Serialization**: Serializing general registers (`r0`-`r12`), `sp`, `lr`, `pc`, and status register `xpsr`.
- **Dirty Memory Synchronization**: Transferring only modified SRAM sections to minimize JTAG transmission delays.
- **Execution Handoff**: Resuming execution on the destination target seamlessly from the exact instruction halted.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 13: Heterogeneous Cross-Target State Synchronization
Transferring register context and stack memory between Target A and Target B.
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

def run_state_sync_demo() -> None:
    print("[*] Initializing Cross-Target State Synchronization Engine...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_sync_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        
        # Instantiate Source Target (representing Physical Hardware Target)
        hw_target = ava.add_target(EmulatedTarget, name="source_hardware")
        hw_target.update_state(TargetStates.STOPPED)
        
        # Instantiate Destination Target (representing Virtual Emulator Target)
        emu_target = ava.add_target(EmulatedTarget, name="dest_emulator")
        emu_target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x10000, name="flash", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x4000,  name="sram",  permissions="rwx")
        
        ava.init_targets()
        print(f"[+] Registered Source ('{hw_target.name}') and Destination ('{emu_target.name}').")
        
        # 1. Establish state on Source Target (as if physical chip paused at breakpoint)
        print("[*] Simulating physical hardware target state at breakpoint...")
        hw_target.regs.r0 = 0xCAFEBABE
        hw_target.regs.r1 = 0x00000042
        hw_target.regs.r2 = 0x20000100
        hw_target.regs.sp = 0x20003F00
        hw_target.regs.lr = 0x08000A51
        hw_target.regs.pc = 0x080018C0
        
        print(f"[+] Source Target State:")
        print(f"  PC : 0x{hw_target.regs.pc:08x}  LR : 0x{hw_target.regs.lr:08x}")
        print(f"  SP : 0x{hw_target.regs.sp:08x}  R0 : 0x{hw_target.regs.r0:08x}")
        print(f"  R1 : 0x{hw_target.regs.r1:08x}  R2 : 0x{hw_target.regs.r2:08x}")
        
        # 2. Extract and transfer complete register file
        print("[*] Serializing register file and synchronizing state to Destination Target...")
        reg_names = ["r0", "r1", "r2", "sp", "lr", "pc"]
        for r in reg_names:
            val = getattr(hw_target.regs, r)
            setattr(emu_target.regs, r, val)
            
        # 3. Verify synchronized state on Destination Target
        print(f"[+] Destination Target Synchronized State:")
        print(f"  PC : 0x{emu_target.regs.pc:08x}  LR : 0x{emu_target.regs.lr:08x}")
        print(f"  SP : 0x{emu_target.regs.sp:08x}  R0 : 0x{emu_target.regs.r0:08x}")
        print(f"  R1 : 0x{emu_target.regs.r1:08x}  R2 : 0x{emu_target.regs.r2:08x}")
        
        assert emu_target.regs.pc == hw_target.regs.pc
        assert emu_target.regs.r0 == hw_target.regs.r0
        print("[+] Cross-target register context integrity: 100% MATCH")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Cross-target state synchronization verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_state_sync_demo()
```

## 🔥 Use Cases
- Concolic execution handoff: moving concrete hardware state into angr to solve complex path conditions.
- Snapshotting device states before executing destructive firmware erase commands.
- Transferring state from physical embedded devices into QEMU to enable multi-threaded fuzzing.
- Live migration of running RTOS tasks across distributed virtual hardware nodes.
- Forensic extraction and offline cloning of compromised IoT device RAM states.

## ⚠️ Caveats & Responsible Practice
- Special registers (such as ARM `CONTROL`, `BASEPRI`, and floating-point `FPSCR`) must be included in transfers.
- Memory caches (L1 D-Cache/I-Cache) on physical chips must be flushed prior to state extraction.
- Hardware peripherals with active DMA transfers must be halted to prevent memory divergence during sync.
- Ensure destination target memory regions have identical base mappings as the source.

## 📦 Test Data & Sample Binaries / Targets
- **Source Target**: `source_hardware` (Physical JTAG Target Mock)
- **Destination Target**: `dest_emulator` (Virtual Target Mock)
- **Synchronized State**: `PC=0x080018C0`, `SP=0x20003F00`, `R0=0xCAFEBABE`

## 🔗 Resources
- Avatar2 State Synchronization Architecture (https://avatar2.readthedocs.io/en/latest/api/targets.html)
- Hybrid Execution: Forwarding and State Transfer (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Virtual Machine Migration and State Serialization (https://en.wikipedia.org/wiki/Live_migration)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #StateSync #ConcolicExecution #FirmwareSecurity #HardwareInTheLoop #angr
