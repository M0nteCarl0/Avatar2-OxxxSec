# ⚡️ 🧠 Hybrid Dynamic-Symbolic Firmware Analysis with angr with Avatar2 Framework (Python practice)
_Post 18/30 · Avatar2 firmware orchestration playbook_

When analyzing firmware binaries protected by cryptographic challenges, hardcoded passcodes, or complex CRC integrity checks, pure dynamic execution gets stuck at conditional branches.

## 🧠 Core Concept
- **Hybrid Dynamic-Symbolic Execution**: Seamlessly transitioning from concrete CPU emulation into symbolic space.
- **State Migration to angr `SimState`**: Initializing an angr state using live registers and memory from Avatar2.
- **Symbolic Variable Marking**: Designating memory buffers (passwords, PINs, challenge nonces) as symbolic bitvectors.
- **SMT Constraint Solving (Z3)**: Mathematically solving for input bytes that satisfy path exploration targets.
- **Concrete State Reinjection**: Injecting solver results back into the physical hardware or emulator target.

## 💻 Key Calls
```python
image, instructions = assemble_firmware()
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="firmware_core")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash_code", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram_data", permissions="rwx")
ava.init_targets()
solved = solve_symbolically(image)
solved = brute_force_with_unicorn(image)
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
```

## 🔥 Use Cases
- Bypassing cryptographic hash and signature checks in embedded bootloaders.
- Automated discovery of valid serial keys, activation tokens, and factory test commands.
- Path exploration to reach deeply nested error handling and vulnerability sink routines.
- Solving complex state machine transitions in industrial Modbus/BACnet IoT stacks.
- Neutralizing anti-tamper logic by solving challenge-response handshake algorithms.

## ⚠️ Caveats
- Path explosion is the primary risk in symbolic execution; restrict symbolic exploration depth to small functions.
- Floating-point and complex non-linear arithmetic can drastically slow down SMT solvers.
- Memory references with symbolic pointers (symbolic addressing) can result in state splitting across entire RAM banks.
- Ensure that memory mapped I/O variables are concretized before passing state to angr to avoid infinite symbolic models.

## 📦 Target
- **Target Routine**: `check_passcode()` @ `0x08001420`
- **Algebraic Constraint**: `((PIN ^ 0x5A5A) * 3) == 0x12345`
- **Solved PIN**: `0x3B4D` (Decimal: 15181)

## 🔗 Resources
- angr Binary Analysis Framework (https://angr.io/)
- Avatar2 angr Integration Architecture (https://avatar2.readthedocs.io/en/latest/api/targets.html)
- Symbolic Execution Principles in Embedded Systems (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)

**Runnable source, run log & report**: [`18_hybrid_symbolic_execution_angr`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/18_hybrid_symbolic_execution_angr)

#Avatar2 #angr #SymbolicExecution #ReverseEngineering #SMT #BinaryAnalysis #Z3
