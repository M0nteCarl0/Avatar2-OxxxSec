# ⚡️ 🔄 Heterogeneous Cross-Target State Synchronization (Python practice)

One of the most powerful workflows enabled by Avatar2 is hybrid target switching: executing firmware on real silicon until an interesting function is reached, then transferring the entire execution state (registers, memory pages, stack) into an emulator or symbolic execution engine (like angr) for in-depth analysis, and finally pushing the solved state back onto hardware.

## 🧠 Core Concept
- **Heterogeneous State Transfer**: Copying CPU registers and memory pages between dissimilar targets (e.g. OpenOCD -> QEMU).
- `synchronize_state()` Protocol: Coordinating state serialization, target halting, and state restoration.
- **Register Bank Serialization**: Serializing general registers (`r0`-`r12`), `sp`, `lr`, `pc`, and status register `xpsr`.
- **Dirty Memory Synchronization**: Transferring only modified SRAM sections to minimize JTAG transmission delays.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 13: Heterogeneous Cross-Target State Synchronization.
Transfers register context and stack memory between Target A and Target B."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

REGS = ("r0", "r1", "r2", "sp", "lr", "pc")


class EmulatedTarget(DummyTarget):
    """Stand-in target exposing a register file that can be migrated."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), dict.fromkeys(REGS, 0))()


def run_state_sync_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    hw_target = ava.add_target(EmulatedTarget, name="source_hardware")
    emu_target = ava.add_target(EmulatedTarget, name="dest_emulator")
    for target in (hw_target, emu_target):
        target.update_state(TargetStates.STOPPED)
    ava.init_targets()

    for name, value in (("r0", 0xCAFEBABE), ("r1", 0x42), ("sp", 0x20003F00),
                        ("lr", 0x08000A51), ("pc", 0x080018C0)):
        setattr(hw_target.regs, name, value)         # board stopped on a breakpoint
    print(f"[*] source   PC=0x{hw_target.regs.pc:08x} R0=0x{hw_target.regs.r0:08x}")

    snapshot = {name: getattr(hw_target.regs, name) for name in REGS}
    for name, value in snapshot.items():             # replay the context off-board
        setattr(emu_target.regs, name, value)
    print(f"[+] restored PC=0x{emu_target.regs.pc:08x} SP=0x{emu_target.regs.sp:08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_state_sync_demo()
```

## 🔥 Use Cases
- Concolic execution handoff: moving concrete hardware state into angr to solve complex path conditions.
- Snapshotting device states before executing destructive firmware erase commands.
- Transferring state from physical embedded devices into QEMU to enable multi-threaded fuzzing.
- Live migration of running RTOS tasks across distributed virtual hardware nodes.

## ⚠️ Caveats & Responsible Practice
- Special registers (such as ARM `CONTROL`, `BASEPRI`, and floating-point `FPSCR`) must be included in transfers.
- Memory caches (L1 D-Cache/I-Cache) on physical chips must be flushed prior to state extraction.
- Hardware peripherals with active DMA transfers must be halted to prevent memory divergence during sync.

## 📦 Test Data & Sample Binaries
- **Source Target**: `source_hardware` (Physical JTAG Target Mock)
- **Destination Target**: `dest_emulator` (Virtual Target Mock)
- **Synchronized State**: `PC=0x080018C0`, `SP=0x20003F00`, `R0=0xCAFEBABE`

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #StateSync #ConcolicExecution #FirmwareSecurity #HardwareInTheLoop #angr
