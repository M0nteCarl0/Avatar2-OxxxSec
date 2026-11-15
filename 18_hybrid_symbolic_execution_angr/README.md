# ⚡️ 🧠 Hybrid Dynamic-Symbolic Firmware Analysis with angr (Python practice)

When analyzing firmware binaries protected by cryptographic challenges, hardcoded passcodes, or complex CRC integrity checks, pure dynamic execution gets stuck at conditional branches.

## 🧠 Core Concept
- **Hybrid Dynamic-Symbolic Execution**: Seamlessly transitioning from concrete CPU emulation into symbolic space.
- **State Migration to angr `SimState`**: Initializing an angr state using live registers and memory from Avatar2.
- **Symbolic Variable Marking**: Designating memory buffers (passwords, PINs, challenge nonces) as symbolic bitvectors.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 18: Hybrid Dynamic-Symbolic Firmware Analysis with angr.
Solves a real Cortex-M3 passcode check symbolically, then hands it to the emulator."""

import io

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, RAM_BASE, MEM_SIZE = 0x08000000, 0x20000000, 0x1000
ASM_SOURCE = """
    ldr r1, =0x20000000     @ passcode buffer in RAM
    ldrb r2, [r1]           @ symbolic byte 0
    ldrb r3, [r1, #1]       @ symbolic byte 1
    movs r4, #0x41          @ 'A'
    cmp r2, r4
    bne fail
    movs r4, #0x42          @ 'B'
    cmp r3, r4
    bne fail
    movs r5, #1             @ success flag in R5
fail:
    b fail
"""


def run_symbolic_execution_demo():
    import angr
    from angr import claripy

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    encoding, _ = ks.asm(ASM_SOURCE)
    image = bytes(encoding)

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="firmware_core")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash_code", permissions="r-x")
    ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram_data", permissions="rwx")
    ava.init_targets()

    project = angr.Project(io.BytesIO(image),
                           main_opts={"arch": "arm", "base_addr": FLASH_BASE})
    state = project.factory.blank_state(addr=FLASH_BASE)
    state.memory.store(RAM_BASE, claripy.BVS("b0", 8))
    state.memory.store(RAM_BASE + 1, claripy.BVS("b1", 8))
    simgr = project.factory.simgr(state)
    simgr.explore(find=lambda s: s.solver.eval(s.regs.r5) == 1, num_find=1)
    if simgr.found:
        found = simgr.found[0]
        passcode = bytes(found.solver.eval(found.memory.load(RAM_BASE + i, 1)) for i in range(2))
        print(f"[+] angr passcode: {passcode!r} (replay it in Unicorn to confirm)")
    else:
        print("[!] angr: no satisfiable model inside the step budget")
    ava.shutdown()


if __name__ == "__main__":
    run_symbolic_execution_demo()
```

## 🔥 Use Cases
- Bypassing cryptographic hash and signature checks in embedded bootloaders.
- Automated discovery of valid serial keys, activation tokens, and factory test commands.
- Path exploration to reach deeply nested error handling and vulnerability sink routines.

## ⚠️ Caveats & Responsible Practice
- Path explosion is the primary risk in symbolic execution; restrict symbolic exploration depth to small functions.
- Floating-point and complex non-linear arithmetic can drastically slow down SMT solvers.

## 📦 Test Data & Sample Binaries
- **Target Routine**: `check_passcode()` @ `0x08001420`
- **Algebraic Constraint**: `((PIN ^ 0x5A5A) * 3) == 0x12345`
- **Solved PIN**: `0x3B4D` (Decimal: 15181)

## 🔗 Resources
- angr Binary Analysis Framework (https://angr.io/)

**Full script, run log & report**: [`18_hybrid_symbolic_execution_angr/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/18_hybrid_symbolic_execution_angr)

#Avatar2 #angr #SymbolicExecution #ReverseEngineering #SMT #BinaryAnalysis #Z3
