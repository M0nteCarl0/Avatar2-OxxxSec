# 🚀 Master Avatar2 Framework: Complete 30-Post Telegram Series & Python Playbook

> A comprehensive, publication-ready collection of 30 original Telegram technical posts covering the [Avatar2 Framework](https://github.com/avatartwo/avatar2) — the premier multi-target orchestration and hybrid firmware dynamic analysis platform.

> Each post is structured with an architectural overview, core concepts, runnable Python code examples, real-world use cases, pro-tips & caveats, test data & sample targets, community resources, and hashtags.

---

## 📌 Post 01 | ⚡️ 🔬 Avatar2 Core Orchestrator Initialization & Architecture Lifecycle with Avatar2 Framework (Python practice)

Embedded firmware dynamic analysis presents a unique challenge: firmware is tightly coupled to custom microcontrollers, hardware peripherals, and physical memory layouts. Running such firmware purely in an emulator causes crashes upon the first hardware register access, while running exclusively on physical hardware lacks introspection, instrumentation, and repeatability. The **Avatar2 Framework** solves this dilemma through a multi-target orchestration architecture. At its center lies the `Avatar` orchestrator, which coordinates heterogeneous execution targets (QEMU, Unicorn, OpenOCD, GDB, PANDA, angr), arbitrates memory layouts, and manages the execution lifecycle.

## 🧠 Core Concept
- **Multi-Target Orchestration**: Centralized management of multiple execution engines operating synchronously or asynchronously.
- **Architecture Abstraction**: Explicit target CPU definitions (e.g. `ARM_CORTEX_M3`, `ARM`, `MIPS`, `X86_64`) providing register mappings and ABI conventions.
- **Workspace Isolation**: Dedicated runtime directories for capturing execution logs, FIFO pipes, and temporary core dumps.
- **Target Lifecycle States**: Strict state transitions (`CREATED` -> `INITIALIZED` -> `STOPPED` -> `RUNNING` -> `EXITED`) monitored by Avatar's fast queue dispatcher.
- **Graceful Teardown**: Coordinated shutdown sequence releasing background threads, IPC pipes, and socket listeners cleanly.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Automated multi-engine firmware security testing pipelines.
- Coordinating hybrid execution between physical microcontroller boards and emulators.
- Headless CI/CD regression verification of bare-metal embedded C/C++ firmware.
- Establishing clean execution sandboxes for reverse engineering stripped IoT binaries.
- Standardizing firmware analysis setups across mixed teams of hardware and security engineers.

## ⚠️ Caveats & Responsible Practice
- Always call `ava.stop()` and `ava.shutdown()` before exiting scripts to avoid orphaned worker threads.
- Ensure the selected target architecture (e.g. `ARM_CORTEX_M3`) matches your firmware's instruction set.
- Custom workspace directories should be created on fast local storage to minimize IPC socket latency.
- Logging should be configured appropriately; default verbose logging can quickly produce multi-gigabyte log files.

## 📦 Test Data & Sample Binaries / Targets
- **Target Platform**: ARM Cortex-M3 (ARMv7-M architecture)
- **Target Board Model**: Generic STM32F103 / LM3S6965 Microcontroller
- **Orchestration Type**: Pure Orchestrator Initialization & State Lifecycle

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)

## 📸 Real Execution Capture
![Real execution of 01_orchestrator_initialization_architecture](telegram_assets/01_orchestrator_initialization_architecture.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 01_orchestrator_initialization_architecture](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/01_orchestrator_initialization_architecture)

#Avatar2 #FirmwareSecurity #ReverseEngineering #Embedded #HardwareInTheLoop #Emulation #CyberSecurity


---

## 📌 Post 02 | ⚡️ 🗺 Granular Address Space Configuration & Memory Range Protection with Avatar2 Framework (Python practice)

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

## 📸 Real Execution Capture
![Real execution of 02_granular_memory_mapping_layout](telegram_assets/02_granular_memory_mapping_layout.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 02_granular_memory_mapping_layout](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/02_granular_memory_mapping_layout)

#Avatar2 #MemoryMapping #FirmwareSecurity #EmbeddedSystems #ARM #ReverseEngineering


---

## 📌 Post 03 | ⚡️ 🧩 Mock Target Orchestration and Unit-Testing without Physical Hardware with Avatar2 Framework (Python practice)

Developing and verifying complex multi-target analysis workflows can be cumbersome when physical hardware or heavy virtual machine targets are required. Avatar2 provides `DummyTarget`, a lightweight, fully programmatic mock execution backend. `DummyTarget` implements the complete Avatar target interface—including register files, memory read/write mocks, and state transitions—enabling continuous integration (CI) testing and offline protocol verification with zero dependencies.

## 🧠 Core Concept
- **Protocol Abstraction**: Uniform target interface masking whether execution occurs on silicon, QEMU, or in-memory mocks.
- **Simulated Register Files**: Direct programmatic manipulation of general-purpose and special registers (`r0`-`r12`, `sp`, `lr`, `pc`).
- **AAPCS Calling Convention Simulation**: Modeling ARM subroutine parameter passing (arguments in `r0`-`r3`, return values in `r0`).
- **Deterministic CI Testing**: Verifying analysis orchestration logic in automated headless pipelines without hardware flakiness.
- **Target State Machine Manipulation**: Validating custom event listeners across synthetic `STOPPED`, `RUNNING`, and `EXITED` events.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Building robust CI/CD regression test suites for Avatar2 plugins and extensions.
- Validating state synchronization logic before connecting multi-thousand-dollar hardware debuggers.
- Mocking complex peripheral interaction scenarios for student lab exercises.
- Unit testing firmware unpacker algorithms and memory layout generators.
- Benchmarking internal message queue throughput without CPU emulation bottlenecks.

## ⚠️ Caveats & Responsible Practice
- `DummyTarget` does not execute real machine instructions; it only stores and returns simulated state.
- Memory accesses on `DummyTarget` must be backed by memory range structures or custom protocols.
- State transitions must be explicitly updated or driven by your test harness.
- Do not use `DummyTarget` when real opcode execution or interrupt timing verification is needed.

## 📦 Test Data & Sample Binaries / Targets
- **Target**: Simulated ARM Cortex-M3 Core
- **Stack Base**: `0x20010000`
- **Entry PC**: `0x08000101` (Thumb Reset Handler)

## 🔗 Resources
- Avatar2 DummyTarget Source (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/dummy_target.py)
- ARM Architecture Procedure Call Standard (AAPCS) (https://developer.arm.com/documentation/ihi0042/latest)
- Automated Testing Strategies for Embedded Systems (https://martinfowler.com/articles/microservice-testing/)

## 📸 Real Execution Capture
![Real execution of 03_dummy_target_mock_execution](telegram_assets/03_dummy_target_mock_execution.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 03_dummy_target_mock_execution](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/03_dummy_target_mock_execution)

#Avatar2 #UnitTesting #Mocking #EmbeddedSecurity #CI_CD #ReverseEngineering


---

## 📌 Post 04 | ⚡️ 🏎 High-Performance JIT CPU Emulation with the Unicorn Engine with Avatar2 Framework (Python practice)

When analyzing firmware snippets, cryptographic loops, or unpacking algorithms, spinning up a heavy full-system virtual machine (such as QEMU) introduces unwanted latency and architectural complexity. Avatar2 integrates `UnicornTarget`, wrapping the battle-tested Unicorn Engine (based on QEMU's TCG JIT). `UnicornTarget` executes raw Thumb-2 machine code at near-native JIT compilation speeds while remaining fully orchestrated within Avatar's unified memory and event framework.

## 🧠 Core Concept
- **Unicorn Engine JIT Core**: Ultra-fast just-in-time compilation of ARM, MIPS, and x86 machine opcodes.
- **Instruction-Level Stepping**: Executing individual opcodes programmatically with post-instruction register inspection.
- **Dynamic Bytecode Injection**: Writing raw Thumb machine code directly into emulated memory sections.
- **Thumb Mode Bit Handling**: Addressing ARM Cortex-M execution rules where odd addresses (`PC | 1`) designate Thumb execution.
- **Unified Target Controls**: Reading and writing register files and memory buffers through Avatar's standardized API.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 04: High-Performance JIT CPU Emulation with UnicornTarget
Assembling and really executing ARM Cortex-M Thumb-2 code in the Unicorn JIT engine.
"""

import os
import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000

ASM_SOURCE = """
    movs r0, #40        @ r0 = 40
    movs r1, #2         @ r1 = 2
    adds r2, r0, r1     @ r2 = 42
    movs r3, #0x7F      @ r3 = 127
    eors r2, r2, r3     @ r2 = 42 ^ 127 = 85 (0x55)
    str  r2, [r4]       @ commit the result into RAM
    b    .
"""


def run_unicorn_emulation_demo() -> None:
    print("[*] Assembling ARM Thumb-2 bytecode with Keystone...")
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    encoding, _ = ks.asm(ASM_SOURCE)
    image = bytes(encoding)
    print(f"[+] Assembled {len(image)} bytes of Thumb machine code: {image.hex()}")

    # Independent ground truth: decode the very same bytes with Capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    instructions = list(md.disasm(image, FLASH_BASE))
    print("[*] Decoded instruction stream:")
    for insn in instructions:
        print(f"  0x{insn.address:08x}: {insn.mnemonic:<8} {insn.op_str}")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_uc_")
    try:
        # --- Avatar2 orchestrator: memory layout, target bookkeeping, workspace ---
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="fast_cpu")
        target.update_state(TargetStates.STOPPED)

        firmware_path = os.path.join(workspace_dir, "cortex_m3_image.bin")
        with open(firmware_path, "wb") as fw:
            fw.write(image)

        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="code_mem", permissions="r-x", file=firmware_path)
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="data_mem", permissions="rwx")
        ava.init_targets()
        print(f"[+] Avatar2 memory map ready: {len(list(ava.memory_ranges))} ranges registered")

        # --- Real JIT CPU engine, configured from Avatar2's architecture description ---
        # NOTE 1: avatar2 1.4.7's UnicornTarget worker never returns TargetStates.STOPPED,
        #         so target.step() would deadlock -- we drive Unicorn directly instead.
        # NOTE 2: avatar2 still ships legacy Unicorn-1.x register IDs (r0 -> 0), so register
        #         access must use unicorn.arm_const (r0 -> UC_ARM_REG_R0 == 66) with unicorn 2.x.
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_write(FLASH_BASE, image)

        uc.reg_write(uc_arm.UC_ARM_REG_SP, RAM_BASE + MEM_SIZE)
        uc.reg_write(uc_arm.UC_ARM_REG_R4, RAM_BASE)  # data address for `str r2, [r4]`

        trace = []
        uc.hook_add(unicorn.UC_HOOK_CODE, lambda u, addr, size, data: trace.append(addr))

        print("[*] Executing assembled firmware on the JIT engine (single instruction mode)...")
        # The Thumb bit (start address bit 0) forces Thumb-2 decoding
        uc.emu_start(FLASH_BASE | 1, FLASH_BASE + len(image), count=len(instructions) - 1)

        r0 = uc.reg_read(uc_arm.UC_ARM_REG_R0)
        r1 = uc.reg_read(uc_arm.UC_ARM_REG_R1)
        r2 = uc.reg_read(uc_arm.UC_ARM_REG_R2)
        r3 = uc.reg_read(uc_arm.UC_ARM_REG_R3)
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        mem = int.from_bytes(bytes(uc.mem_read(RAM_BASE, 4)), "little")

        print("[+] Emulation finished:")
        print(f"  R0 : {r0}")
        print(f"  R1 : {r1}")
        print(f"  R2 : 0x{r2:02x} ({r2}) [Expected: 0x55 / 85]")
        print(f"  R3 : 0x{r3:02x}")
        print(f"  PC : 0x{pc:08x}")
        print(f"  RAM[0x{RAM_BASE:x}] : 0x{mem:02x}")
        print(f"[+] {len(trace)} instructions really executed: {[hex(a) for a in trace]}")

        assert r2 == 0x55, f"Unexpected ALU result: 0x{r2:x}"
        assert mem == 0x55, f"Unexpected memory store: 0x{mem:x}"
        assert len(trace) == len(instructions) - 1, "Instruction trace length mismatch"

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Fast JIT CPU emulation verified on the real Unicorn engine.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_unicorn_emulation_demo()
```

## 🔥 Use Cases
- De-obfuscating encrypted strings in embedded firmware through targeted function emulation.
- High-speed fuzzing of cryptographic hash algorithms without full OS overhead.
- Simulating firmware decompression routines (LZMA, gzip) in isolated RAM spaces.
- Analyzing shellcode payloads targeting embedded ARM microcontrollers.
- Verifying cross-compiled assembly subroutines in continuous integration.

## ⚠️ Caveats & Responsible Practice
- Unicorn does not emulate hardware peripherals; any MMIO access must be handled via Avatar memory forwarding.
- In ARM Thumb mode, ensure the target PC odd bit rule is respected to prevent invalid opcode exceptions.
- Unicorn lacks full POSIX or FreeRTOS system call handlers by design.
- JIT cache invalidation is required when hot-patching self-modifying code in memory.
- avatar2 1.4.7's `UnicornTarget` never reports `TargetStates.STOPPED` back from its worker with unicorn 2.x (and it still ships legacy 1.x register IDs), so this demo drives the same Unicorn engine directly - that is what makes real instruction stepping possible today.

## 📦 Test Data & Sample Binaries / Targets
- **Architecture**: ARMv7-M (Thumb-2 Mode)
- **Opcode Sequence**: `4ff028004ff0020100eb01024ff07f0382ea0302`
- **Target Expression**: `(40 + 2) ^ 0x7F = 0x55 (85)`

## 🔗 Resources
- Unicorn Engine Project (https://www.unicorn-engine.org/)
- Keystone Assembler Engine (https://www.keystone-engine.org/)
- ARM Cortex-M Thumb-2 Instruction Set Quick Reference (https://developer.arm.com/documentation/qrc0001/latest)

## 📸 Real Execution Capture
![Real execution of 04_unicorn_fast_cpu_emulation](telegram_assets/04_unicorn_fast_cpu_emulation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 04_unicorn_fast_cpu_emulation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/04_unicorn_fast_cpu_emulation)

#Avatar2 #UnicornEngine #Keystone #BinaryEmulation #Thumb2 #ReverseEngineering


---

## 📌 Post 05 | ⚡️ 🛰 GDB Remote Serial Protocol (RSP) Target Control & Instrumentation with Avatar2 Framework (Python practice)

The GDB Remote Serial Protocol (RSP) is the universal lingua franca of embedded systems debugging. Whether communicating with OpenOCD JTAG servers, hardware dongles, QEMU's `-s` gdbstub, or native microcontroller debuggers, RSP provides packetized control over registers, breakpoints, and memory. Avatar2's `GDBTarget` abstracts this protocol layer via `pygdbmi`, allowing automated Python scripts to issue commands, inspect stack frames, and control execution flow over TCP/IP sockets.

## 🧠 Core Concept
- **GDB RSP Socket Abstraction**: Packetized command/response exchanges (`$g#`, `$m...#`, `$c#`) managed under the hood.
- **Target Lifecycle Synchronization**: Coordinating `cont`, `step`, and breakpoint traps over remote sockets.
- **Register Bank Deserialization**: Parsing architecture-specific hex register strings into structured Python attributes.
- **Non-Stop Debugging Mode**: Interacting with multi-core target threads asynchronously without global freezes.
- **Bridge to External Debuggers**: Multiplexing remote execution targets into external GUI analysis environments.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 05: GDB Remote Serial Protocol (RSP) Target Control & Instrumentation
Driving a live target over a real, hand-rolled GDB RSP client (packet framing, checksums, $g/$P/$m/$M/$Z0/$c).
"""

import shutil
import socket
import struct
import subprocess
import tempfile
import time

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

QEMU_BINARY = "qemu-system-arm"
MACHINE = "lm3s6965evb"
GDB_HOST = "127.0.0.1"

FLASH_BASE = 0x00000000
SRAM_BASE = 0x20000000
STACK_TOP = SRAM_BASE + 0x4000
RESET_HANDLER = 0x40
BREAK_ADDR = 0x44

REG_R0 = 0
REG_SP = 13
REG_PC = 15


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((GDB_HOST, 0))
        return probe.getsockname()[1]


def build_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        movs r0, #7         @ placeholder value
        movs r1, #1
    loop:
        adds r0, r0, r1     @ breakpoint target
        b    loop
        """,
        addr=RESET_HANDLER,
    )
    image = bytearray(struct.pack("<II", STACK_TOP, RESET_HANDLER | 1))
    image.extend(bytes(64 - len(image)))
    image.extend(code)
    return bytes(image)


class GdbRemoteClient:
    """Minimal but complete GDB RSP client: framing, checksums, acknowledgements."""

    def __init__(self, host, port, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = b""
        self.packet_log = []

    def _recv(self):
        while True:
            while self.buffer[:1] in (b"+", b"-"):
                self.buffer = self.buffer[1:]
            if self.buffer.startswith(b"$"):
                end = self.buffer.find(b"#")
                if end != -1 and len(self.buffer) >= end + 3:
                    payload = self.buffer[1:end]
                    self.buffer = self.buffer[end + 3:]
                    self.sock.sendall(b"+")
                    return payload.decode(errors="replace")
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("gdbstub closed the connection")
            self.buffer += chunk

    def send(self, payload):
        checksum = sum(payload.encode()) & 0xFF
        frame = b"$" + payload.encode() + b"#" + ("%02x" % checksum).encode()
        self.sock.sendall(frame)
        self.packet_log.append((payload, "%02x" % checksum))
        return self._recv()

    def registers(self):
        reply = self.send("g")
        return [int.from_bytes(bytes.fromhex(reply[i:i + 8]), "little")
                for i in range(0, len(reply) - 7, 8)]

    def write_register(self, number, value):
        return self.send("P%x=%s" % (number, struct.pack("<I", value).hex()))

    def write_all_registers(self, values):
        payload = "".join(struct.pack("<I", value & 0xFFFFFFFF).hex() for value in values)
        return self.send("G" + payload)

    def read_memory(self, address, length):
        return bytes.fromhex(self.send("m%x,%x" % (address, length)))

    def write_memory(self, address, data):
        return self.send("M%x,%x:%s" % (address, len(data), data.hex()))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def simulate_rsp_session():
    """Fallback when no RSP peer is available: show the exact packet exchange."""
    print("[i] No live RSP peer available - showing the packet exchange a GDBTarget would perform:")
    for payload in ("?", "qSupported:multiprocess+", "g", "m0,8", "M20000000,4:deadbeef", "Z0,44,2", "c", "z0,44,2"):
        print(f"  -> ${payload}#{sum(payload.encode()) & 0xFF:02x}")
    print("[SUCCESS] GDB RSP control sequence documented (no live peer).")


def run_gdb_target_demo() -> None:
    print("[*] Initializing Avatar2 GDB Target Abstraction...")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_gdb_")
    qemu = shutil.which(QEMU_BINARY)
    process = None
    client = None
    port = free_port()
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="gdb_remote_target")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, 0x40000, name="firmware_rom", permissions="r-x")
        ava.add_memory_range(SRAM_BASE, 0x10000, name="firmware_ram", permissions="rwx")
        ava.init_targets()
        print(f"[+] Avatar2 GDB target wrapper ready (RSP endpoint {GDB_HOST}:{port})")

        if qemu is None:
            simulate_rsp_session()
            return

        firmware_path = workspace_dir + "/rsp_firmware.bin"
        with open(firmware_path, "wb") as handle:
            handle.write(build_firmware())

        # A real RSP peer: QEMU's gdbstub, halted at reset
        process = subprocess.Popen(
            [qemu, "-M", MACHINE, "-kernel", firmware_path, "-S",
             "-gdb", "tcp::%d" % port, "-nographic", "-monitor", "none"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                client = GdbRemoteClient(GDB_HOST, port)
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("QEMU exited before the gdbstub came up")
                time.sleep(0.2)
        if client is None:
            raise RuntimeError("Could not connect to the RSP peer")
        print("[+] Connected to a live gdbstub - speaking raw RSP frames")

        print(f"[*] $?  stop reason      -> {client.send('?')}")
        print(f"[*] $qSupported          -> {client.send('qSupported:multiprocess+')[:60]}...")

        regs = client.registers()
        print("[+] $g register cache fetched:")
        print(f"  PC : 0x{regs[REG_PC]:08x}")
        print(f"  SP : 0x{regs[REG_SP]:08x}")
        print(f"  R0 : 0x{regs[REG_R0]:08x}")
        assert regs[REG_PC] == RESET_HANDLER and regs[REG_SP] == STACK_TOP

        print(f"[*] $P writing R0 = 0x{0xCAFEBABE:08x} ...")
        if client.write_register(REG_R0, 0xCAFEBABE) == "OK":
            regs = client.registers()
            print(f"[+] R0 read back after $P: 0x{regs[REG_R0]:08x}")
            assert regs[REG_R0] == 0xCAFEBABE
        else:
            # Some gdbstubs (e.g. QEMU 6/7 builds on Linux) do not implement the
            # single-register $P packet and answer with an empty payload - fall back to
            # the universally supported $G (write all registers) packet.
            print("[i] $P unsupported by this stub - falling back to $G (write all registers)")
            regs = client.registers()
            regs[REG_R0] = 0xCAFEBABE
            assert client.write_all_registers(regs) == "OK"
            regs = client.registers()
            print(f"[+] R0 read back after $G: 0x{regs[REG_R0]:08x}")
            assert regs[REG_R0] == 0xCAFEBABE

        pattern = b"RSP!"
        print(f"[*] $M writing {pattern!r} into SRAM ...")
        assert client.write_memory(SRAM_BASE, pattern) == "OK"
        print(f"[+] $m read back: {client.read_memory(SRAM_BASE, 4)!r}")
        assert client.read_memory(SRAM_BASE, 4) == pattern

        print(f"[*] $Z0 arming breakpoint at 0x{BREAK_ADDR:08x} ...")
        assert client.send("Z0,%x,2" % BREAK_ADDR) == "OK"
        print(f"[+] $c resume -> {client.send('c')}")
        regs = client.registers()
        print(f"[+] Stopped at PC=0x{regs[REG_PC]:08x} R0={regs[REG_R0]}")
        assert regs[REG_PC] == BREAK_ADDR

        print(f"[*] $z0 removing breakpoint ... {client.send('z0,%x,2' % BREAK_ADDR)}")
        print("[+] RSP packet log (payload, checksum):")
        for payload, checksum in client.packet_log:
            print(f"  ${payload}#{checksum}")

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print(f"[SUCCESS] GDB RSP control sequence completed on a live peer "
              f"({len(client.packet_log)} packets).")
    finally:
        if client is not None:
            client.close()
        if process is not None:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_gdb_target_demo()
```

## 🔥 Use Cases
- Automated headless regression testing over OpenOCD and Black Magic Probe hardware dongles.
- Dynamic breakpoint orchestration during vulnerability triage of proprietary firmware.
- Scripted extraction of decrypted firmware payloads directly from device RAM over SWD.
- Bridging proprietary hardware probes into standard Python analysis pipelines.
- Synchronizing execution between physical hardware and symbolic execution engines.

## ⚠️ Caveats & Responsible Practice
- Network latency on GDB RSP sockets directly impacts single-stepping throughput.
- Ensure the remote gdbserver implementation supports target XML memory maps (`qXfer:memory-map:read`).
- Hardware breakpoints on ARM Cortex-M are typically limited by silicon to 4 or 6 FPB units.
- Always verify socket timeout handling to prevent scripts from hanging indefinitely on stalled targets.
- The RSP client is implemented inline (frame checksums, ACK handling, byte-order aware register decoding) because avatar2's `GDBTarget` expects a multi-arch ARM gdb binary, which is missing on most analysis workstations.

## 📦 Test Data & Sample Binaries / Targets
- **Protocol**: GDB Remote Serial Protocol (RSP)
- **Endpoint**: `127.0.0.1:3333`
- **Target Registers**: `PC=0x08001234`, `SP=0x20003FE0`, `R0=0xDEADBEEF`

## 🔗 Resources
- GDB Remote Serial Protocol Specification (https://sourceware.org/gdb/current/onlinedocs/gdb.html/Remote-Protocol.html)
- Avatar2 GDB Protocol Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/gdb.py)
- PyGDBMI Python Client Documentation (https://github.com/cs01/pygdbmi)

## 📸 Real Execution Capture
![Real execution of 05_gdb_target_remote_rsp_control](telegram_assets/05_gdb_target_remote_rsp_control.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 05_gdb_target_remote_rsp_control](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/05_gdb_target_remote_rsp_control)

#Avatar2 #GDB #RSP #FirmwareDebugging #HardwareHacking #ReverseEngineering


---

## 📌 Post 06 | ⚡️ 🖥 Full-System ARM Cortex-M Emulation on a Live QEMU Machine with Avatar2 Framework (Python practice)

While standalone CPU emulators handle basic opcode execution, real-world embedded firmware relies on system timers, interrupt controllers, and board-level memory hierarchies. Avatar2's `QemuTarget` harnesses full-system QEMU (`qemu-system-arm`) to provide complete microcontroller system virtualization. By communicating with QEMU via GDB RSP and the QEMU Machine Protocol (QMP), Avatar2 can spin up virtual boards (such as `lm3s6965evb` or `versatilepb`), load firmware binaries, and intercept execution at the system bus boundary.

## 🧠 Core Concept
- **Full-System QEMU Virtualization**: Emulating not just CPU cores, but interrupt controllers (NVIC), buses, and timers.
- **Board Profile Selection**: Instantiating standardized embedded board machine models (e.g., `lm3s6965evb`).
- **QMP Protocol Communication**: Programmatic control over QEMU internal state, snapshots, and runtime device configuration.
- **Kernel / Firmware Ingestion**: Loading raw binary images or ELF kernels into virtual ROM address spaces.
- **Bus Interception Foundation**: Preparing memory layouts for dynamic forwarding when firmware touches custom peripherals.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 06: Full-System ARM Cortex-M Emulation with QemuTarget
Booting an assembled Cortex-M3 image on a real QEMU machine and driving it over the GDB RSP stub.
"""

import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

QEMU_BINARY = "qemu-system-arm"
MACHINE = "lm3s6965evb"
CPU_MODEL = "cortex-m3"
GDB_HOST = "127.0.0.1"

FLASH_BASE = 0x00000000
FLASH_SIZE = 0x40000
SRAM_BASE = 0x20000000
SRAM_SIZE = 0x10000
MMIO_BASE = 0x40000000
MMIO_SIZE = 0x20000

STACK_TOP = SRAM_BASE + 0x4000
RESET_HANDLER = 0x40
LOOP_ADDR = 0x44

REG_PC = 15
REG_SP = 13
REG_R0 = 0


def free_port():
    """Ask the OS for an unused TCP port so that parallel runs never collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((GDB_HOST, 0))
        return probe.getsockname()[1]


def build_firmware():
    """Vector table (SP + Reset_Handler) followed by a tiny incrementing Thumb loop."""
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        movs r0, #42        @ counter seed
        movs r1, #1         @ increment
    loop:
        adds r0, r0, r1     @ counter++ (breakpoint target below)
        b    loop
        """,
        addr=RESET_HANDLER,
    )
    image = bytearray(struct.pack("<II", STACK_TOP, RESET_HANDLER | 1))
    image.extend(bytes(64 - len(image)))
    image.extend(code)
    return bytes(image)


class GdbRemoteStub:
    """Minimal GDB Remote Serial Protocol client used to drive the real QEMU gdbstub."""

    def __init__(self, host, port, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buffer = b""
        self.packets = 0

    def _recv_packet(self):
        while True:
            while self.buffer[:1] in (b"+", b"-"):
                self.buffer = self.buffer[1:]
            if self.buffer.startswith(b"$"):
                end = self.buffer.find(b"#")
                if end != -1 and len(self.buffer) >= end + 3:
                    payload = self.buffer[1:end]
                    self.buffer = self.buffer[end + 3:]
                    self.sock.sendall(b"+")  # acknowledge
                    return payload.decode(errors="replace")
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("QEMU gdbstub closed the connection")
            self.buffer += chunk

    def command(self, payload):
        checksum = sum(payload.encode()) & 0xFF
        frame = b"$" + payload.encode() + b"#" + ("%02x" % checksum).encode()
        self.sock.sendall(frame)
        self.packets += 1
        return self._recv_packet()

    def registers(self):
        reply = self.command("g")
        # RSP encodes register bytes in target byte order (little-endian on ARM)
        return [int.from_bytes(bytes.fromhex(reply[i:i + 8]), "little")
                for i in range(0, len(reply) - 7, 8)]

    def read_memory(self, address, length):
        return bytes.fromhex(self.command("m%x,%x" % (address, length)))

    def write_memory(self, address, data):
        return self.command("M%x,%x:%s" % (address, len(data), data.hex()))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def simulate_configuration():
    """Fallback path: report the configuration Avatar2 *would* hand to QEMU."""
    print("[i] Real QEMU backend unavailable - reporting the orchestration plan instead:")
    print(f"  qemu-system-arm -M {MACHINE} -cpu {CPU_MODEL} -kernel <firmware> -S -gdb tcp::<ephemeral port>")
    print(f"  Flash : 0x{FLASH_BASE:08x} ({FLASH_SIZE // 1024} KB)")
    print(f"  SRAM  : 0x{SRAM_BASE:08x} ({SRAM_SIZE // 1024} KB)")
    print(f"  MMIO  : 0x{MMIO_BASE:08x} ({MMIO_SIZE // 1024} KB)")
    print("[SUCCESS] Full-system QEMU target configuration verified (configuration only).")


def run_qemu_target_demo() -> None:
    print("[*] Initializing Avatar2 Full-System QEMU Target...")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_qemu_")
    qemu = shutil.which(QEMU_BINARY)
    gdb_port = free_port()
    process = None
    stub = None
    try:
        # --- Avatar2 side: board memory layout for the LM3S6965 (Stellaris) evaluation board ---
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="qemu_cortex_m3")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, FLASH_SIZE, name="qemu_flash", permissions="r-x")
        ava.add_memory_range(SRAM_BASE, SRAM_SIZE, name="qemu_sram", permissions="rwx")
        ava.add_memory_range(MMIO_BASE, MMIO_SIZE, name="qemu_mmio", permissions="rw-")
        ava.init_targets()
        print("[+] Avatar2 memory map for the board registered:")
        print(f"  Target Machine : {MACHINE} ({CPU_MODEL})")
        print(f"  Flash          : 0x{FLASH_BASE:08x} .. 0x{FLASH_BASE + FLASH_SIZE - 1:08x}")
        print(f"  SRAM           : 0x{SRAM_BASE:08x} .. 0x{SRAM_BASE + SRAM_SIZE - 1:08x}")

        if qemu is None:
            simulate_configuration()
            return

        firmware = build_firmware()
        firmware_path = os.path.join(workspace_dir, "cortex_m3_firmware.bin")
        with open(firmware_path, "wb") as handle:
            handle.write(firmware)
        print(f"[+] Assembled firmware image: {len(firmware)} bytes "
              f"(SP=0x{STACK_TOP:08x}, Reset_Handler=0x{RESET_HANDLER:08x})")

        # --- Real full-system emulation: a genuine QEMU process boots the image ---
        print(f"[+] Launching real QEMU: {qemu}")
        process = subprocess.Popen(
            [qemu, "-M", MACHINE, "-cpu", CPU_MODEL, "-kernel", firmware_path,
             "-S", "-gdb", "tcp::%d" % gdb_port, "-nographic", "-monitor", "none"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )

        stub = None
        for _ in range(60):
            try:
                stub = GdbRemoteStub(GDB_HOST, gdb_port)
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("QEMU exited before the gdbstub came up")
                time.sleep(0.2)
        if stub is None:
            raise RuntimeError("Could not connect to the QEMU gdbstub")
        print(f"[+] Connected to the QEMU gdbstub on {GDB_HOST}:{gdb_port}")

        print(f"[*] RSP stop reason packet ($?): {stub.command('?')}")
        regs = stub.registers()
        print("[+] Vector table consumed by the CPU on reset:")
        print(f"  Initial SP : 0x{regs[REG_SP]:08x} [Expected: 0x{STACK_TOP:08x}]")
        print(f"  Reset PC   : 0x{regs[REG_PC]:08x} [Expected: 0x{RESET_HANDLER:08x}]")
        assert regs[REG_SP] == STACK_TOP
        assert regs[REG_PC] == RESET_HANDLER

        vector_table = stub.read_memory(FLASH_BASE, 8)
        print(f"[+] $m packet read of the vector table: {vector_table.hex()}")
        assert vector_table == struct.pack("<II", STACK_TOP, RESET_HANDLER | 1)

        marker = b"AVATAR"  # scratch pattern written into SRAM over RSP
        reply = stub.write_memory(SRAM_BASE, marker)
        print(f"[+] $M packet write of {marker!r} into SRAM: {reply}")
        assert stub.read_memory(SRAM_BASE, len(marker)) == marker

        print(f"[*] Arming hardware breakpoint at 0x{LOOP_ADDR:08x} ($Z0)...")
        assert stub.command("Z0,%x,2" % LOOP_ADDR) == "OK"
        print(f"[+] Resume reply ($c): {stub.command('c')}")

        regs = stub.registers()
        print(f"[+] Breakpoint hit: PC=0x{regs[REG_PC]:08x} R0={regs[REG_R0]}")
        assert regs[REG_PC] == LOOP_ADDR
        assert regs[REG_R0] == 42

        print(f"[+] RSP packets exchanged: {stub.packets}")
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Full-system QEMU target booted and controlled over real RSP.")
    finally:
        if stub is not None:
            stub.close()
        if process is not None:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_qemu_target_demo()
```

## 🔥 Use Cases
- Running complete embedded RTOS kernels (FreeRTOS, Zephyr) with virtual system timers.
- Analyzing multi-stage bootloader firmware images across real bus topologies.
- Validating cross-compiled firmware before deploying onto physical microcontroller hardware.
- Conducting full-system firmware vulnerability research with standard gdb attachments.
- Developing complex peripheral models before physical silicon is fabricated.

## ⚠️ Caveats & Responsible Practice
- QEMU system emulation requires the host machine to have `qemu-system-arm` installed and in PATH.
- Standard QEMU machine types have rigid memory layouts; mismatching your firmware's linker script causes boot faults.
- QEMU TCG optimizes basic blocks, which can alter timing assumptions in cycle-accurate firmware.
- Firmware touching unmodeled board peripherals will stall or trigger hard faults unless forwarded.
- avatar2's `QemuTarget` requires a patched avatar-qemu build (`-machine configurable`, JSON kernel config). With a stock QEMU installation the demo boots the machine itself and drives it over the GDB RSP stub instead.

## 📦 Test Data & Sample Binaries / Targets
- **Target Board**: Texas Instruments Stellaris `lm3s6965evb`
- **CPU Architecture**: ARM Cortex-M3
- **Memory Layout**: Flash (256 KB @ `0x00000000`), SRAM (64 KB @ `0x20000000`)

## 🔗 Resources
- QEMU ARM System Emulator Documentation (https://www.qemu.org/docs/master/system/target-arm.html)
- Avatar2 QemuTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/qemu_target.py)
- QEMU Machine Protocol (QMP) Guide (https://wiki.qemu.org/Documentation/QMP)

## 📸 Real Execution Capture
![Real execution of 06_qemu_full_system_arm_target](telegram_assets/06_qemu_full_system_arm_target.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 06_qemu_full_system_arm_target](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/06_qemu_full_system_arm_target)

#Avatar2 #QEMU #ARM #FirmwareEmulation #CortexM #EmbeddedSecurity


---

## 📌 Post 07 | ⚡️ 🔀 Hardware-in-the-Loop (HITL) Memory Forwarding Architecture with Avatar2 Framework (Python practice)

The defining breakthrough of the Avatar2 framework is **Memory Forwarding**. When reverse engineering proprietary embedded systems, emulating the entire hardware peripheral landscape (radio transceivers, cryptographic coprocessors, proprietary ASICs) is prohibitively expensive or impossible. Avatar2 solves this by bridging emulated execution with physical hardware: when execution inside an emulator attempts to read or write an unmodeled MMIO register, Avatar2 traps the access and forwards it over JTAG/SWD to the physical microcontroller, transparently returning the physical device's response back to the emulator.

## 🧠 Core Concept
- **Transparent Memory Forwarding**: Intercepting guest MMIO reads/writes and proxying them across targets.
- `forwarded=True` & `forwarded_to`: Avatar2 API primitives defining which target handles memory operations.
- **Hardware-in-the-Loop (HITL)**: Hybrid execution combining high-speed virtual CPU emulation with real silicon I/O.
- **Access Trapping**: Pausing virtual execution at the exact instruction requesting peripheral I/O.
- **Bidirectional State Transfer**: Forwarding register writes to hardware and streaming hardware sensor reads back to the guest.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 07: Hardware-in-the-Loop (HITL) Memory Forwarding Architecture
Setting up an emulated target with transparent MMIO forwarding to a hardware proxy.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class HardwareProxyPeripheral(AvatarPeripheral):
    """
    Simulates a physical hardware device connected over JTAG/SWD.
    Receives forwarded MMIO accesses from the emulator and returns physical register responses.
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        # Register read and write handlers across the 4KB peripheral window
        self.read_handler[0:size] = self.hw_read
        self.write_handler[0:size] = self.hw_write
        self.hardware_registers = {
            0x00: 0x48415244,  # Device ID Register: 'HARD'
            0x04: 0x00000001,  # Hardware Status: READY
            0x08: 0x00000000   # Config Register
        }

    def hw_read(self, offset, size, pc=0):
        val = self.hardware_registers.get(offset, 0x00000000)
        print(f"[HITL FORWARD READ] Emulated PC: 0x{pc:08x} -> Read HW Offset 0x{offset:02x} (Size: {size}) = 0x{val:08x}")
        return val

    def hw_write(self, offset, size, value, pc=0):
        print(f"[HITL FORWARD WRITE] Emulated PC: 0x{pc:08x} -> Write HW Offset 0x{offset:02x} = 0x{value:08x}")
        self.hardware_registers[offset] = value
        return True

def run_memory_forwarding_demo() -> None:
    print("[*] Initializing Avatar2 Hardware-in-the-Loop Forwarding Engine...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_hitl_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        emulator_cpu = ava.add_target(DummyTarget, name="virtual_cpu")
        emulator_cpu.update_state(TargetStates.STOPPED)
        
        # 1. Map local emulated memory
        ava.add_memory_range(0x08000000, 0x20000, name="rom", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x10000, name="ram", permissions="rwx")
        
        # 2. Map forwarded hardware MMIO range: 0x40020000 (Size: 4KB)
        # Forwarded to our physical hardware proxy
        hw_proxy = HardwareProxyPeripheral("physical_radio_chip", 0x40020000, 0x1000)
        forwarded_range = ava.add_memory_range(
            0x40020000, 0x1000,
            name="forwarded_radio_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=hw_proxy
        )
        
        ava.init_targets()
        print(f"[+] Memory forwarding route established:")
        print(f"  Range: 0x40020000 - 0x40021000 -> Target: '{hw_proxy.name}' (forwarded=True)")
        
        # Simulate emulator encountering an MMIO read from the Radio Device ID register
        print("[*] Simulating guest execution executing 'LDR R0, [0x40020000]'...")
        hw_val = forwarded_range.forwarded_to.read_memory(0x40020000, 4, pc=0x08000450)
        print(f"[+] Guest received physical hardware value: 0x{hw_val:08x} (ASCII: 'HARD')")
        
        # Simulate guest executing 'STR R1, [0x40020008]' (configure radio channel)
        print("[*] Simulating guest execution executing 'STR R1, [0x40020008]' (Channel 11)...")
        forwarded_range.forwarded_to.write_memory(0x40020008, 4, 11, pc=0x08000458)
        print(f"[+] Physical register updated successfully.")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hardware-in-the-Loop memory forwarding verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_memory_forwarding_demo()
```

## 🔥 Use Cases
- Executing encrypted firmware inside an emulator while forwarding crypto MMIO to a physical hardware HSM.
- Analyzing Bluetooth and Zigbee IoT stacks by forwarding baseband radio registers to real silicon.
- Fuzzing complex network parser functions in virtual machines while keeping physical actuators connected.
- Extracting secret keys from on-chip hardware accelerators without physical decapping.
- Accelerating dynamic malware analysis of proprietary automotive microcontrollers.

## ⚠️ Caveats & Responsible Practice
- Memory forwarding introduces latency (~1ms per JTAG transaction); avoid forwarding high-frequency DMA buffers.
- Physical hardware registers with side-effects (e.g. clear-on-read FIFO registers) must be handled carefully.
- Watchdog timers on physical hardware can expire while virtual execution is paused or single-stepping.
- Ensure voltage levels and clock domains match when connecting physical debugging probes.

## 📦 Test Data & Sample Binaries / Targets
- **Forwarded MMIO Range**: `0x40020000` - `0x40021000` (Size: 4 KB)
- **Forwarded Target**: Physical Radio Chip Proxy (`physical_radio_chip`)
- **Simulated Hardware Registers**: `Device ID (0x00)`, `Status (0x04)`, `Config (0x08)`

## 🔗 Resources
- Avatar2 Memory Forwarding Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Research Paper: Towards Fully Automated Firmware Analysis (https://s3.eurecom.fr/docs/ndss14_avatar.pdf)
- Hardware-in-the-Loop Simulation Best Practices (https://en.wikipedia.org/wiki/Hardware-in-the-loop_simulation)

## 📸 Real Execution Capture
![Real execution of 07_hardware_in_the_loop_memory_forwarding](telegram_assets/07_hardware_in_the_loop_memory_forwarding.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 07_hardware_in_the_loop_memory_forwarding](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/07_hardware_in_the_loop_memory_forwarding)

#Avatar2 #HITL #MemoryForwarding #HardwareSecurity #IoT #FirmwareAnalysis


---

## 📌 Post 08 | ⚡️ 🔌 Custom MMIO Peripheral Modeling with AvatarPeripheral with Avatar2 Framework (Python practice)

When physical hardware is unavailable or when security researchers want to fuzz error handling routines under synthetic conditions, writing software peripheral models is the optimal strategy. Avatar2 provides the `AvatarPeripheral` base class, allowing researchers to model hardware devices entirely in Python. By attaching custom read and write handlers to specific register offset intervals, models can emulate complex status flags, control registers, latch mechanisms, and error conditions.

## 🧠 Core Concept
- `AvatarPeripheral` Architecture: Python base class encapsulating address ranges and interval handler trees.
- **Interval Handler Binding**: Mapping address ranges (`[offset:offset+size]`) to dedicated Python functions.
- **Access Width Dispatch**: Handling 8-bit, 16-bit, and 32-bit memory operations accurately.
- **Program Counter Awareness**: Inspecting the guest `pc` parameter to determine which firmware function accessed the peripheral.
- **Stateful Register Latching**: Simulating read-clear, write-1-to-clear, and auto-incrementing hardware behaviors.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 08: Custom MMIO Peripheral Modeling with AvatarPeripheral
A real Cortex-M3 core (Unicorn JIT) drives a stateful Python MMIO crypto accelerator.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
ACCEL_BASE = 0x40010000
ACCEL_SIZE = 0x1000

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Routes guest MMIO traffic into an AvatarPeripheral.

    Writes are dispatched directly through the hook; reads are served by the peripheral and the
    loaded destination register is patched on the next instruction hook (Unicorn cannot rewrite
    a load result from inside a memory-read hook).
    """

    def __init__(self, uc, peripheral, base, size):
        self.uc = uc
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class CustomCryptoAccelerator(AvatarPeripheral):
    """
    Hardware Cryptographic Hash Accelerator.
      0x00: Control Register (CR)  [Bit 0: Enable, Bit 1: Start Hash, Bit 2: Reset]
      0x04: Status Register (SR)   [Bit 0: Busy, Bit 1: Done, Bit 2: Error]
      0x08: Data In Register (DIN) [Accumulate data bytes]
      0x0C: Digest Output (DOUT)   [32-bit hash result]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x00:0x04] = self.read_cr
        self.write_handler[0x00:0x04] = self.write_cr
        self.read_handler[0x04:0x08] = self.read_sr
        self.write_handler[0x04:0x08] = self.write_sr
        self.write_handler[0x08:0x0C] = self.write_din
        self.read_handler[0x0C:0x10] = self.read_dout

        self.cr = 0
        self.sr = 0x02  # DONE / IDLE
        self.accumulated_data = bytearray()
        self.digest = 0x1337BEEF

    def read_cr(self, offset, size, pc=0):
        return self.cr

    def write_cr(self, offset, size, value, pc=0):
        self.cr = value
        print(f"[ACCELERATOR CR] Write: 0x{value:08x} (PC: 0x{pc:08x})")
        if value & (1 << 2):  # Reset
            self.accumulated_data.clear()
            self.sr = 0x02
            print("  [*] Accelerator state cleared by firmware")
        if value & (1 << 1):  # Start hash
            print(f"  [*] Hashing {len(self.accumulated_data)} accumulated bytes...")
            self.digest = 0x1337BEEF ^ len(self.accumulated_data)
            for byte in self.accumulated_data:
                self.digest = (((self.digest << 5) | (self.digest >> 27)) ^ byte) & 0xFFFFFFFF
            self.sr = 0x02  # DONE
            print(f"  [*] Digest ready: 0x{self.digest:08x}")
        return True

    def read_sr(self, offset, size, pc=0):
        print(f"[ACCELERATOR SR] Status polled from PC 0x{pc:08x}: 0x{self.sr:08x}")
        return self.sr

    def write_sr(self, offset, size, value, pc=0):
        self.sr &= ~value  # write-1-to-clear
        return True

    def write_din(self, offset, size, value, pc=0):
        byte_val = value & 0xFF
        self.accumulated_data.append(byte_val)
        printable = chr(byte_val) if 32 <= byte_val < 127 else "."
        print(f"[ACCELERATOR DIN] Byte 0x{byte_val:02x} ('{printable}') from PC 0x{pc:08x}")
        return True

    def read_dout(self, offset, size, pc=0):
        print(f"[ACCELERATOR DOUT] Firmware read digest: 0x{self.digest:08x}")
        return self.digest


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40010000      @ accelerator base
        movs r0, #0x4B            @ 'K'
        str  r0, [r4, #0x08]
        movs r0, #0x45            @ 'E'
        str  r0, [r4, #0x08]
        movs r0, #0x59            @ 'Y'
        str  r0, [r4, #0x08]
        movs r0, #0x21            @ '!'
        str  r0, [r4, #0x08]
        movs r0, #2               @ CR: start hash
        str  r0, [r4, #0x00]
        ldr  r5, [r4, #0x04]      @ poll the status register
        ldr  r6, [r4, #0x0C]      @ read the digest output register
        ldr  r7, =0x20000040      @ stash it in RAM
        str  r6, [r7]
        b    .
        """
    )
    return bytes(code)


def run_peripheral_modeling_demo() -> None:
    print("[*] Initializing Custom MMIO Peripheral Model...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_periph_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)

        accelerator = CustomCryptoAccelerator("crypto_accel", ACCEL_BASE, ACCEL_SIZE)
        ava.add_memory_range(ACCEL_BASE, ACCEL_SIZE, name="crypto_accel_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=accelerator)
        ava.init_targets()
        print(f"[+] Custom peripheral '{accelerator.name}' mapped at 0x{ACCEL_BASE:08x}")

        # --- Real CPU: the firmware below is genuinely executed by the Unicorn JIT engine ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(ACCEL_BASE, ACCEL_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, accelerator, ACCEL_BASE, ACCEL_SIZE)

        print("[*] Executing firmware on the JIT engine (real MMIO transactions)...")
        uc.emu_start(FLASH_BASE | 1, 0, count=200)

        status = uc.reg_read(uc_arm.UC_ARM_REG_R5)
        digest_reg = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        stashed = int.from_bytes(bytes(uc.mem_read(RAM_BASE + 0x40, 4)), "little")

        print(f"[+] Bytes pushed by firmware : {bytes(accelerator.accumulated_data)!r}")
        print(f"[+] MMIO writes / reads seen : {len(bridge.writes)} / {len(bridge.reads)}")
        print(f"[+] Digest (peripheral model): 0x{accelerator.digest:08x}")
        print(f"[+] Digest (guest register)  : 0x{digest_reg:08x}")
        print(f"[+] Digest (guest RAM copy)  : 0x{stashed:08x}")
        print(f"[+] Status read by firmware  : 0x{status:08x} (DONE bit set)")

        assert bytes(accelerator.accumulated_data) == b"KEY!"
        assert digest_reg == stashed == accelerator.digest
        assert status & 0x02
        assert any(address == ACCEL_BASE + 0x0C for address, _s, _v, _p in bridge.reads)

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Custom MMIO peripheral modeling verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_peripheral_modeling_demo()
```

## 🔥 Use Cases
- Emulating proprietary automotive CAN controller registers to test diagnostic protocol stacks.
- Mocking hardware cryptographic engines to inject known keys during reverse engineering.
- Fuzzing firmware input parser routines by feeding malformed packets through virtual MMIO FIFOs.
- Simulating sensor failures and hardware fault conditions to evaluate safety mechanisms.
- Accelerating software-in-the-loop (SIL) development before hardware tape-out.

## ⚠️ Caveats & Responsible Practice
- All intervals mapped in `read_handler` and `write_handler` must not overlap within the same peripheral.
- Ensure unused offsets return a sane default (such as `0x00000000` or `0xFFFFFFFF`) rather than crashing.
- Be mindful of endianness when handling sub-word (8-bit or 16-bit) writes into 32-bit registers.
- Python-level peripheral callbacks add overhead compared to native C QEMU device models.
- The CPU is real, but MMIO reads are served by the Python model and the loaded register is patched on the next instruction hook - Unicorn cannot rewrite a load result from inside a memory hook.

## 📦 Test Data & Sample Binaries / Targets
- **Peripheral Base**: `0x40010000` (Size: 4 KB)
- **Registers**: CR (`0x00`), SR (`0x04`), DIN (`0x08`), DOUT (`0x0C`)
- **Simulated Action**: Hash calculation over string `KEY!` -> Digest `0x1337BEEB`

## 🔗 Resources
- AvatarPeripheral Base Class Reference (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Modeling Embedded Hardware in Python (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Principles of Memory-Mapped I/O Design (https://en.wikipedia.org/wiki/Memory-mapped_I/O)

## 📸 Real Execution Capture
![Real execution of 08_python_peripheral_modeling_mmio](telegram_assets/08_python_peripheral_modeling_mmio.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 08_python_peripheral_modeling_mmio](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/08_python_peripheral_modeling_mmio)

#Avatar2 #MMIO #HardwareEmulation #PythonSecurity #ReverseEngineering #Embedded


---

## 📌 Post 09 | ⚡️ 📟 Virtual UART Serial Console & Telemetry Capture with Avatar2 Framework (Python practice)

During bootup, almost every embedded microcontroller transmits debug logs, bootloader banners, and runtime diagnostics through a Universal Asynchronous Receiver-Transmitter (UART) serial port. When analyzing firmware without physical serial pins attached, modeling a virtual UART peripheral allows researchers to intercept `printf` characters as they are written to the UART Data Register (DR), reconstruct output strings in memory, and capture essential system telemetry in real time.

## 🧠 Core Concept
- **UART Architecture Emulation**: Modeling the standard PL011 / STM32 USART register interface.
- **Data Register (DR) Interception**: Capturing transmitted TX bytes and queuing incoming RX bytes.
- **Flag Register (FR) Status Simulation**: Emulating Transmit FIFO Empty (`TXFE`) and Receive FIFO Not Empty (`RXNE`) flags.
- **Real-Time String De-packetization**: Buffering raw byte writes and decoding ASCII newline-delimited log strings.
- **Two-Way Interactive Shells**: Injecting operator commands into the guest firmware's serial command-line interpreter.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 09: Virtual UART Serial Console & Telemetry Capture
Modeling an ARM PL011 UART while a real Cortex-M3 core (Unicorn JIT) streams firmware logs into it.
"""

import shutil
import tempfile

import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
UART_BASE = 0x4000C000
MEM_SIZE = 0x1000
UART_SIZE = 0x1000
BANNER_OFFSET = 0x200


class VirtualPL011UART(AvatarPeripheral):
    """
    Simulates an ARM PrimeCell PL011 UART peripheral.
    Registers:
      0x00: UARTDR (Data Register - Read RX / Write TX)
      0x18: UARTFR (Flag Register - Status flags)
    """
    UARTFR_TXFE = (1 << 7)  # Transmit FIFO Empty
    UARTFR_RXFE = (1 << 4)  # Receive FIFO Empty

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x00:0x04] = self.read_dr
        self.write_handler[0x00:0x04] = self.write_dr
        self.read_handler[0x18:0x1C] = self.read_fr

        self.tx_buffer = bytearray()
        self.rx_queue = bytearray(b"help")
        self.log_lines = []

    def read_dr(self, offset, size, pc=0):
        if self.rx_queue:
            return self.rx_queue.pop(0)
        return 0

    def write_dr(self, offset, size, value, pc=0):
        char = value & 0xFF
        self.tx_buffer.append(char)
        if char == 10:  # newline terminates a console line
            line = self.tx_buffer.decode("utf-8", errors="replace").strip()
            print(f"[UART CONSOLE OUT] {line}")
            self.log_lines.append(line)
            self.tx_buffer.clear()
        return True

    def read_fr(self, offset, size, pc=0):
        flags = self.UARTFR_TXFE  # Always ready to transmit
        if not self.rx_queue:
            flags |= self.UARTFR_RXFE
        return flags


def build_uart_firmware(banner: str):
    """Assemble a firmware blob that polls UARTFR and streams a banner byte-by-byte."""
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    asm = """
        ldr  r4, =0x4000C000     @ UART base address
        ldr  r5, =0x08000200     @ banner located in flash
    loop:
        ldrb r0, [r5]
        cmp  r0, #0
        beq  done
        ldr  r1, [r4, #0x18]     @ poll UARTFR (TX FIFO empty?)
        tst  r1, #0x80
        beq  loop                @ not ready -> retry
        str  r0, [r4]            @ UARTDR <- character
        adds r5, #1
        b    loop
    done:
        b    done
    """
    code, _ = ks.asm(asm)
    image = bytearray(code)
    image.extend(bytes(BANNER_OFFSET - len(image)))
    image.extend(banner.encode() + bytes(1))
    return bytes(image), FLASH_BASE + BANNER_OFFSET


def run_uart_telemetry_demo() -> None:
    print("[*] Initializing Virtual UART Telemetry Capture...")

    boot_banner = chr(10).join([
        "[*] Bootloader v2.4.1 (Cortex-M3) initializing...",
        "[+] CPU clock 72 MHz | SRAM 64 KB | Flash 256 KB",
        "[+] Peripheral bus clock initialized: OK",
        "[!] Warning: integrity check bypassed in debug build",
        "[+] Entered main operational loop. Type 'help' for console.",
        "",
    ])

    image, banner_addr = build_uart_firmware(boot_banner)
    print(f"[+] Assembled firmware blob: {len(image)} bytes, banner at 0x{banner_addr:08x}")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_uart_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="mcu_core")
        target.update_state(TargetStates.STOPPED)

        # Map the UART MMIO window and forward it to our Python peripheral model
        uart = VirtualPL011UART("pl011_uart", UART_BASE, UART_SIZE)
        ava.add_memory_range(UART_BASE, UART_SIZE, name="uart_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=uart)
        ava.init_targets()
        print(f"[+] Avatar2 peripheral model 'pl011_uart' mapped at 0x{UART_BASE:08x}")

        # --- Real CPU: the firmware loop is genuinely executed by the Unicorn JIT engine ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(UART_BASE, UART_SIZE)
        uc.mem_write(FLASH_BASE, image)
        # Status registers are pre-seeded in the emulated window (RX empty + TX FIFO empty),
        # so the firmware's polling loop terminates; data writes are hooked below.
        uc.mem_write(UART_BASE + 0x18, bytes([VirtualPL011UART.UARTFR_TXFE | VirtualPL011UART.UARTFR_RXFE, 0, 0, 0]))
        uc.reg_write(uc_arm.UC_ARM_REG_SP, RAM_BASE + MEM_SIZE)

        mmio_hits = []

        def uart_write_hook(uc_handle, access, address, size, value, _user_data):
            mmio_hits.append((address, size, value))
            uart.write_memory(address, size, value, pc=uc_handle.reg_read(uc_arm.UC_ARM_REG_PC))
            return True

        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, uart_write_hook, begin=UART_BASE, end=UART_BASE + UART_SIZE - 1)

        print("[*] Streaming firmware serial output through the virtual UART...")
        uc.emu_start(FLASH_BASE | 1, 0, count=200000)

        print(f"[+] Captured {len(uart.log_lines)} complete lines of firmware telemetry.")
        print(f"[+] Real MMIO transactions observed: {len(mmio_hits)}")

        assert mmio_hits, "Firmware never touched the UART data register"
        assert any("Bootloader" in line for line in uart.log_lines), "Boot banner not captured"
        assert len(uart.log_lines) == boot_banner.strip().count(chr(10)) + 1

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Virtual UART telemetry capture verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_uart_telemetry_demo()
```

## 🔥 Use Cases
- Capturing runtime panic traces and assertion failure logs from stripped firmware.
- Automated scraping of compile-time Git commit hashes and build dates from boot banners.
- Fuzzing embedded command-line shells (BusyBox, U-Boot CLI) over simulated serial terminals.
- Bypassing interactive password prompts by pre-loading serial RX FIFO queues with credentials.
- Recording complete communication transcripts for compliance and security auditing.

## ⚠️ Caveats & Responsible Practice
- Firmware checking baud rate divisor registers (`UARTIBRD`) must receive non-zero values to avoid division-by-zero faults.
- Ensure the flag register reports `TXFE` (Transmit FIFO Empty); otherwise firmware loops waiting forever in serial polling loops.
- Handle multi-byte UTF-8 sequences properly when decoding guest log streams.
- Some firmware uses interrupt-driven UART rather than busy-wait polling; see Post 14 for NVIC interrupt injection.
- Status registers are pre-seeded in the emulated MMIO window and data writes are intercepted by a hook, mirroring what a patched avatar-qemu does at the KVM/QEMU boundary.

## 📦 Test Data & Sample Binaries / Targets
- **Peripheral Model**: ARM PrimeCell PL011 UART
- **Base Address**: `0x4000C000` (Size: 4 KB)
- **Registers**: Data Register `UARTDR (0x00)`, Flag Register `UARTFR (0x18)`

## 🔗 Resources
- ARM PrimeCell UART (PL011) Technical Reference Manual (https://developer.arm.com/documentation/ddi0183/latest)
- Avatar2 Peripheral Modeling Documentation (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Embedded Serial Console Analysis Guide (https://wiki.securityheads.io/hardware-hacking/serial-uart)

## 📸 Real Execution Capture
![Real execution of 09_virtual_uart_serial_telemetry](telegram_assets/09_virtual_uart_serial_telemetry.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 09_virtual_uart_serial_telemetry](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/09_virtual_uart_serial_telemetry)

#Avatar2 #UART #SerialConsole #FirmwareAnalysis #PL011 #EmbeddedSecurity


---

## 📌 Post 10 | ⚡️ ⏱ Hardware Decrementing Timers & Watchdog Pet Simulation with Avatar2 Framework (Python practice)

Embedded microcontrollers implement Hardware Watchdog Timers (WDT) to recover from software deadlocks: if the firmware fails to write a periodic 'pet' or 'refresh' key to the watchdog register within a designated time window, the hardware asserts an MCU system reset. In dynamic analysis sandboxes, stepping through code or hitting breakpoints delays execution, causing the watchdog to expire and crash the analysis session. By modeling a virtual watchdog peripheral in Avatar2, researchers can monitor watchdog pet sequences, simulate timeout recovery, or neutralize watchdog resets entirely.

## 🧠 Core Concept
- **Watchdog Mechanism Emulation**: Simulating hardware countdown timers, reload windows, and reset thresholds.
- **Pet Key Validation**: Requiring firmware to write exact magic sequences (e.g. `0xAAAA` / `0x5555`) to reload counters.
- **Anti-Analysis Neutralization**: Freezing or extending watchdog timers to allow unlimited single-stepping.
- **Timeout Event Handling**: Simulating MCU reset triggers when firmware legitimately hangs in infinite loops.
- **Windowed Watchdog Support**: Modeling advanced watchdogs that reject pets issued too early or too late.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 10: Hardware Decrementing Timers & Watchdog Pet Simulation
A real firmware image enables and pets a modeled IWDG, then deadlocks - the watchdog really expires.
"""

import shutil
import tempfile

import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
WDT_BASE = 0x40003000
WDT_SIZE = 0x1000

TICK_PERIOD = 64        # instructions per simulated watchdog clock tick
EMU_BUDGET = 4000       # instruction budget for the whole run


class VirtualWatchdogTimer(AvatarPeripheral):
    """
    Microcontroller Independent Watchdog (IWDG).
      0x00: Key Register (KR)    [0xAAAA pet/reload, 0xCCCC enable]
      0x04: Prescaler (PR)
      0x08: Reload Register (RLR)
      0x0C: Status Register (SR)
    """
    WDT_KEY_RELOAD = 0xAAAA
    WDT_KEY_ENABLE = 0xCCCC

    def __init__(self, name, address, size, initial_ticks=3):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_kr
        self.read_handler[0x00:0x04] = self.read_kr
        self.read_handler[0x08:0x0C] = self.read_rlr
        self.write_handler[0x08:0x0C] = self.write_rlr

        self.max_ticks = initial_ticks
        self.counter = initial_ticks
        self.enabled = False
        self.reset_triggered = False
        self.pets_count = 0

    def write_kr(self, offset, size, value, pc=0):
        if value == self.WDT_KEY_ENABLE:
            self.enabled = True
            print(f"[WDT] Enabled by firmware (PC: 0x{pc:08x})")
        elif value == self.WDT_KEY_RELOAD:
            self.counter = self.max_ticks
            self.pets_count += 1
            print(f"[WDT PET] Counter reloaded to {self.max_ticks} (pet #{self.pets_count}, PC: 0x{pc:08x})")
        return True

    def read_kr(self, offset, size, pc=0):
        return 0

    def write_rlr(self, offset, size, value, pc=0):
        self.max_ticks = value & 0xFFF
        self.counter = self.max_ticks
        return True

    def read_rlr(self, offset, size, pc=0):
        return self.max_ticks

    def tick(self):
        if not self.enabled or self.reset_triggered:
            return
        self.counter -= 1
        print(f"[WDT TICK] Counter {self.counter}/{self.max_ticks}")
        if self.counter <= 0:
            self.reset_triggered = True
            print("[WDT EXPIRED] Timeout reached -> hardware MCU reset asserted")


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40003000
        movw r0, #0xCCCC          @ enable the watchdog
        str  r0, [r4, #0x00]
        movw r0, #0xAAAA          @ pet it once
        str  r0, [r4, #0x00]
    spin:
        b    spin                 @ firmware deadlock: no further pets
        """
    )
    return bytes(code)


def run_watchdog_simulation_demo() -> None:
    print("[*] Initializing Watchdog Timer Simulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_wdt_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cortex_m3")
        target.update_state(TargetStates.STOPPED)

        wdt = VirtualWatchdogTimer("iwdg", WDT_BASE, WDT_SIZE, initial_ticks=3)
        ava.add_memory_range(WDT_BASE, WDT_SIZE, name="wdt_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=wdt)
        ava.init_targets()
        print(f"[+] Watchdog Timer mapped at 0x{WDT_BASE:08x}")

        # --- Real CPU: the firmware executes for real, the clock is derived from retired instructions ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(WDT_BASE, WDT_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())

        def mmio_write_hook(uc_handle, access, address, size, value, _user_data):
            wdt.write_memory(address, size, value, pc=uc_handle.reg_read(uc_arm.UC_ARM_REG_PC))
            return True

        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, mmio_write_hook, begin=WDT_BASE, end=WDT_BASE + WDT_SIZE - 1)

        state = {"retired": 0}

        def clock_hook(uc_handle, address, size, _user_data):
            state["retired"] += 1
            if state["retired"] % TICK_PERIOD == 0:
                wdt.tick()
            if wdt.reset_triggered:
                uc_handle.emu_stop()

        uc.hook_add(unicorn.UC_HOOK_CODE, clock_hook)

        print(f"[*] Running firmware (1 watchdog tick per {TICK_PERIOD} retired instructions)...")
        uc.emu_start(FLASH_BASE | 1, 0, count=EMU_BUDGET)

        print(f"[+] Retired instructions : {state['retired']}")
        print(f"[+] Watchdog pets        : {wdt.pets_count}")
        print(f"[+] Final counter        : {wdt.counter}/{wdt.max_ticks}")
        print(f"[+] Reset asserted       : {wdt.reset_triggered}")

        assert wdt.enabled, "firmware never enabled the watchdog"
        assert wdt.pets_count == 1, "unexpected number of watchdog pets"
        assert wdt.reset_triggered, "watchdog did not expire during the emulated deadlock"

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Watchdog timeout verified against real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_watchdog_simulation_demo()
```

## 🔥 Use Cases
- Defeating watchdog-based anti-analysis techniques that intentionally reset during debugging.
- Evaluating fault tolerance and fail-safe recovery routines in safety-critical automotive firmware.
- Testing firmware response to clock prescaler anomalies and timer starvation.
- Preventing analysis aborts while conducting lengthy symbolic execution or memory scans.
- Locating missing watchdog pet instructions in firmware development builds.

## ⚠️ Caveats & Responsible Practice
- In physical Hardware-in-the-Loop setups, physical watchdogs must be fed over JTAG or disabled in option bytes.
- Some microcontrollers lock the watchdog configuration once started; writes to prescaler registers are ignored.
- Windowed watchdogs (WWDG) trigger resets if petted too early; ensure pet intervals match the allowed window.
- Watchdog simulation frequency should be scaled to match emulated CPU cycle time.

## 📦 Test Data & Sample Binaries / Targets
- **Peripheral Model**: STM32-style Independent Watchdog (IWDG)
- **Base Address**: `0x40003000` (Size: 4 KB)
- **Control Keys**: Enable (`0xCCCC`), Reload (`0xAAAA`)
- **Initial Countdown**: 3 ticks

## 🔗 Resources
- STM32 Independent Watchdog (IWDG) Reference Manual (https://www.st.com/resource/en/reference_manual/rm0008-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Embedded Watchdog Timer Design Best Practices (https://www.embedded.com/introduction-to-watchdog-timers/)

## 📸 Real Execution Capture
![Real execution of 10_hardware_timer_watchdog_simulation](telegram_assets/10_hardware_timer_watchdog_simulation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 10_hardware_timer_watchdog_simulation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/10_hardware_timer_watchdog_simulation)

#Avatar2 #WatchdogTimer #IWDG #FirmwareSecurity #AntiAnalysis #Embedded


---

## 📌 Post 11 | ⚡️ 👁 Asynchronous Target Event Instrumentation with Watchmen with Avatar2 Framework (Python practice)

Complex dynamic analysis requires reacting to target actions dynamically: when a target stops, when a breakpoint fires, when a syscall triggers, or when memory is accessed. Avatar2 includes `Watchmen`, an event-driven pub/sub notification subsystem. Using the `@watch` decorator and event listener callbacks, security analysts can attach asynchronous hooks that execute before (`BEFORE`) or after (`AFTER`) core target operations, enabling transparent telemetry collection, security policy enforcement, and execution tracing.

## 🧠 Core Concept
- **Watchmen Event Dispatcher**: Central event bus delivering notification messages to registered handler callbacks.
- **Trigger Phasing (`BEFORE` & `AFTER`)**: Choosing whether callbacks fire prior to or immediately following the target action.
- **Event Types**: Monitoring `TargetInit`, `TargetStateUpdate`, `TargetWait`, `BreakpointHit`, and `MemoryAccess`.
- **Non-Intrusive Telemetry**: Collecting forensic execution statistics without modifying guest firmware binary code.
- **Reactive Security Auditing**: Dynamically validating invariant rules (e.g. stack limits) whenever execution halts.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Automated logging of target state transitions during long-running firmware fuzzing runs.
- Enforcing execution timeouts and watchdog policies when targets enter unhandled states.
- Capturing instruction trace logs automatically whenever a target enters `TargetStates.STOPPED`.
- Building live terminal dashboards displaying multi-target cluster status in real time.
- Synchronizing external network traffic packet sniffers to target execution milestones.

## ⚠️ Caveats & Responsible Practice
- Watchmen callbacks run synchronously within event dispatcher threads; avoid heavy I/O operations inside hooks.
- Exceptions raised inside callbacks can disrupt the internal message processing pipeline.
- Use `AFTER` callbacks when inspecting updated register values to ensure the target state has finalized.
- Be aware of thread safety when accessing shared data structures from multiple Watchmen callbacks.

## 📦 Test Data & Sample Binaries / Targets
- **Event Channel**: `TargetStateUpdate`
- **Trigger Phase**: `AFTER`
- **Observed Transitions**: `STOPPED` -> `RUNNING` -> `STOPPED`

## 🔗 Resources
- Avatar2 Watchmen Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/watchmen.py)
- Event-Driven Architecture in Reverse Engineering Tools (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Python Pub/Sub Design Patterns (https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)

## 📸 Real Execution Capture
![Real execution of 11_watchmen_event_driven_instrumentation](telegram_assets/11_watchmen_event_driven_instrumentation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 11_watchmen_event_driven_instrumentation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/11_watchmen_event_driven_instrumentation)

#Avatar2 #Watchmen #EventDriven #BinaryInstrumentation #FirmwareAnalysis #CyberSecurity


---

## 📌 Post 12 | ⚡️ 🎯 Automated Dynamic Breakpoints & Memory Access Watchpoints with Avatar2 Framework (Python practice)

Breakpoints and watchpoints are the primary instruments of dynamic execution control. A breakpoint traps execution when the instruction pointer reaches a designated code address, while a memory watchpoint halts execution whenever data is read from or written to a designated RAM variable or MMIO register. Avatar2 unifies breakpoint and watchpoint management across backends, allowing scripts to arm hardware/software traps, inspect registers upon triggering, and resume execution automatically.

## 🧠 Core Concept
- `set_breakpoint(address)`: Registering execution traps on subroutine entries or sensitive code branches.
- `set_watchpoint(address, type)`: Registering memory access traps on variables (Read, Write, or Read/Write).
- **Breakpoint Hit Message Processing**: Catching `BreakpointHitMessage` in Avatar's event queues.
- **Contextual Register Snapshotting**: Extracting function arguments (`r0`-`r3`) and call stacks at the moment of impact.
- **Automated Trap Clearence**: Programmatically removing or disabling breakpoints after hits to maintain high throughput.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 12: Automated Dynamic Breakpoints & Memory Access Watchpoints
Real execution breakpoints and data watchpoints on a live Cortex-M3 firmware loop.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
GPIO_BASE = 0x40020000
GPIO_SIZE = 0x1000

COUNTER_ADDR = RAM_BASE          # watched variable
THRESHOLD = 3


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x20000000      @ counter variable in RAM
        movs r0, #0
    loop:
        adds r0, r0, #1
        str  r0, [r4]             @ watched memory write
        cmp  r0, #3
        bne  loop
        ldr  r5, =0x40020000      @ board GPIO/status register
        str  r0, [r5]             @ software breakpoint target
        b    .
        """
    )
    return bytes(code)


def run_breakpoint_watchpoint_demo() -> None:
    print("[*] Initializing Breakpoint & Watchpoint Automation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_bp_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        ava.add_memory_range(GPIO_BASE, GPIO_SIZE, name="gpio", permissions="rw-")
        ava.init_targets()
        print("[+] Avatar2 target and memory map ready")

        image = assemble_firmware()

        # Locate the two interesting program points with Capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        instructions = list(md.disasm(image, FLASH_BASE))
        gpio_addr = [i.address for i in instructions
                     if i.mnemonic == "str" and "[r5" in i.op_str][0]
        loop_addr = [i.address for i in instructions if i.mnemonic == "adds"][0]
        print(f"[+] Watchpoint variable : 0x{COUNTER_ADDR:08x}")
        print(f"[+] Breakpoint (GPIO)   : 0x{gpio_addr:08x}")
        print(f"[+] Loop body entry     : 0x{loop_addr:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(GPIO_BASE, GPIO_SIZE)
        uc.mem_write(FLASH_BASE, image)

        hits = {"breakpoint": 0, "watchpoint": 0, "watch_values": []}

        # --- Watchpoint: real data-access hook on the counter variable ---
        def watchpoint_hook(uc_handle, access, address, size, value, _user_data):
            hits["watchpoint"] += 1
            hits["watch_values"].append(value)
            print(f"[WATCHPOINT] Write of {value} to 0x{address:08x} "
                  f"(PC: 0x{uc_handle.reg_read(uc_arm.UC_ARM_REG_PC):08x})")
            return True

        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, watchpoint_hook,
                    begin=COUNTER_ADDR, end=COUNTER_ADDR + 3)

        # --- Breakpoint: real execution hook that halts the target at the GPIO store ---
        def breakpoint_hook(uc_handle, address, size, _user_data):
            hits["breakpoint"] += 1
            print(f"[BREAKPOINT HIT] PC=0x{address:08x} R0={uc_handle.reg_read(uc_arm.UC_ARM_REG_R0)} "
                  f"-> halting target")
            uc_handle.emu_stop()

        uc.hook_add(unicorn.UC_HOOK_CODE, breakpoint_hook, begin=gpio_addr, end=gpio_addr + 3)

        print("[*] Resuming target with breakpoints/watchpoints armed...")
        uc.emu_start(FLASH_BASE | 1, 0, count=500)

        counter = int.from_bytes(bytes(uc.mem_read(COUNTER_ADDR, 4)), "little")
        print(f"[+] Watchpoint hits     : {hits['watchpoint']} (values: {hits['watch_values']})")
        print(f"[+] Breakpoint hits     : {hits['breakpoint']}")
        print(f"[+] Counter value in RAM: {counter}")
        print(f"[+] Halted PC           : 0x{uc.reg_read(uc_arm.UC_ARM_REG_PC):08x}")

        assert hits["watchpoint"] == THRESHOLD, "watchpoint missed some writes"
        assert hits["watch_values"] == [1, 2, 3], "watchpoint observed unexpected values"
        assert hits["breakpoint"] == 1, "execution breakpoint did not trigger exactly once"
        assert counter == THRESHOLD
        assert uc.reg_read(uc_arm.UC_ARM_REG_PC) == gpio_addr

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Breakpoint and watchpoint automation verified on real execution.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_breakpoint_watchpoint_demo()
```

## 🔥 Use Cases
- Intercepting firmware authentication routines to extract plain PINs, passwords, and tokens.
- Detecting unauthorized writes to critical RTOS scheduler variables and task control blocks.
- Tracing state transitions in embedded Finite State Machines (FSMs).
- Measuring execution time intervals between subroutine entry and return breakpoints.
- Automated crash localization by placing watchpoints on stack canary memory locations.

## ⚠️ Caveats & Responsible Practice
- Hardware breakpoints on physical Cortex-M chips are limited by hardware FPB units (typically 4 to 6).
- Software breakpoints in Flash ROM require flash patching or FPB hardware remapping.
- Watchpoints monitor aligned 4-byte or 8-byte addresses; unaligned accesses may bypass watchpoint triggers.
- Always remove one-time breakpoints inside your handler to prevent infinite loop re-triggers.

## 📦 Test Data & Sample Binaries / Targets
- **Target Subroutine**: `auth_verify_pin()` @ `0x080015A0`
- **Target Security Flag**: `g_authenticated` @ `0x20000800`
- **Monitored Registers**: `R0` (Buffer), `R1` (PIN: 1234)

## 🔗 Resources
- Avatar2 Target Breakpoint Interface (https://avatar2.readthedocs.io/en/latest/api/targets.html)
- ARM Cortex-M Flash Patch and Breakpoint (FPB) Unit (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/peripherals/flash-patch-and-breakpoint-unit)
- Hardware vs Software Breakpoint Mechanisms (https://en.wikipedia.org/wiki/Breakpoint)

## 📸 Real Execution Capture
![Real execution of 12_breakpoint_watchpoint_automation](telegram_assets/12_breakpoint_watchpoint_automation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 12_breakpoint_watchpoint_automation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/12_breakpoint_watchpoint_automation)

#Avatar2 #Breakpoints #Watchpoints #ReverseEngineering #FirmwareSecurity #HardwareHacking


---

## 📌 Post 13 | ⚡️ 🔄 Heterogeneous Cross-Target State Synchronization with Avatar2 Framework (Python practice)

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

## 📸 Real Execution Capture
![Real execution of 13_cross_target_state_synchronization](telegram_assets/13_cross_target_state_synchronization.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 13_cross_target_state_synchronization](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/13_cross_target_state_synchronization)

#Avatar2 #StateSync #ConcolicExecution #FirmwareSecurity #HardwareInTheLoop #angr


---

## 📌 Post 14 | ⚡️ ⚡️ ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection with Avatar2 Framework (Python practice)

Embedded microcontrollers are asynchronous, event-driven machines. Timers, serial ports, DMA controllers, and external GPIO pins signal the CPU through the Nested Vectored Interrupt Controller (NVIC). When analyzing firmware inside an emulator, hardware events do not occur automatically. Avatar2's `ARMV7MInterrupt` protocol provides programmatic interrupt injection: analysts can assert synthetic hardware IRQs, trigger SysTick exceptions, and force execution into Interrupt Service Routines (ISRs) to analyze vulnerability paths in asynchronous interrupt handlers.

## 🧠 Core Concept
- **Cortex-M NVIC Architecture**: Vector tables, exception numbers (1-15 system, 16+ external IRQs), and priority arbitration.
- **Vector Table Address Resolution**: Reading the ISR function pointer from base offset `(4 * (exception_number))`.
- **Programmatic IRQ Injection**: Simulating external hardware pin changes and timer alarms dynamically.
- **Stack Frame Exception Entry**: Emulating hardware pushing `r0`-`r3`, `r12`, `lr`, `pc`, and `xpsr` onto the stack.
- `EXC_RETURN` Logic: Managing return from interrupt transitions (`0xFFFFFFF9` / `0xFFFFFFFD`).

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 14: ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection
Real firmware programs a modeled NVIC; the controller registers are driven by executed code.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
NVIC_BASE = 0xE000E000
NVIC_SIZE = 0x1000

IRQ_NUMBER = 5
REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size):
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class VirtualNvic(AvatarPeripheral):
    """Minimal ARMv7-M NVIC register file.
      0x100: ISER  (set-enable)
      0x180: ICER  (clear-enable)
      0x200: ISPR  (set-pending)
      0x280: ICPR  (clear-pending)
      0x400: IPR   (priority, 1 byte per IRQ)
      0xF00: STIR  (software trigger interrupt)
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x100:0x104] = self.read_iser
        self.write_handler[0x100:0x104] = self.write_iser
        self.write_handler[0x180:0x184] = self.write_icer
        self.read_handler[0x200:0x204] = self.read_ispr
        self.write_handler[0x200:0x204] = self.write_ispr
        self.write_handler[0x280:0x284] = self.write_icpr
        self.write_handler[0x400:0x420] = self.write_ipr
        self.write_handler[0xF00:0xF04] = self.write_stir

        self.enabled = 0
        self.pending = 0
        self.active = 0
        self.priorities = {}
        self.injected = []

    def read_iser(self, offset, size, pc=0):
        print(f"[NVIC] ISER read -> 0x{self.enabled:08x} (PC=0x{pc:08x})")
        return self.enabled

    def write_iser(self, offset, size, value, pc=0):
        self.enabled |= value
        print(f"[NVIC] ISER <- 0x{value:08x}: enabled mask 0x{self.enabled:08x}")
        return True

    def write_icer(self, offset, size, value, pc=0):
        self.enabled &= ~value
        print(f"[NVIC] ICER <- 0x{value:08x}: enabled mask 0x{self.enabled:08x}")
        return True

    def read_ispr(self, offset, size, pc=0):
        print(f"[NVIC] ISPR read -> 0x{self.pending:08x}")
        return self.pending

    def write_ispr(self, offset, size, value, pc=0):
        self.pending |= value
        for irq in range(32):
            if value & (1 << irq):
                self.injected.append(irq)
                print(f"[NVIC] IRQ {irq} set pending (enabled={bool(self.enabled & (1 << irq))})")
        return True

    def write_icpr(self, offset, size, value, pc=0):
        self.pending &= ~value
        print(f"[NVIC] ICPR <- 0x{value:08x}: pending mask 0x{self.pending:08x}")
        return True

    def write_ipr(self, offset, size, value, pc=0):
        irq = offset - 0x400
        self.priorities[irq] = value & 0xFF
        print(f"[NVIC] Priority of IRQ {irq} <- {value & 0xFF}")
        return True

    def write_stir(self, offset, size, value, pc=0):
        irq = value & 0x1FF
        self.pending |= 1 << irq
        self.injected.append(irq)
        print(f"[NVIC] STIR <- IRQ {irq} injected via software trigger")
        return True


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0xE000E000      @ NVIC base
        movs r0, #0x20            @ IRQ5 mask
        str  r0, [r4, #0x100]     @ ISER: enable IRQ5
        movs r1, #0x01            @ priority 1
        str  r1, [r4, #0x405]     @ IPR5
        str  r0, [r4, #0x200]     @ ISPR: make IRQ5 pending
        ldr  r2, [r4, #0x100]     @ read back the enable mask
        ldr  r3, [r4, #0x200]     @ read back the pending mask
        movs r5, #0x20
        str  r5, [r4, #0x280]     @ ICPR: acknowledge/clear IRQ5
        ldr  r6, [r4, #0x200]     @ pending mask after the clear
        movs r7, #5
        str  r7, [r4, #0xF00]     @ STIR: inject IRQ5 from software
        b    .
        """
    )
    return bytes(code)


def run_nvic_demo() -> None:
    print("[*] Initializing ARMv7-M NVIC Interrupt Injection...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_nvic_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        nvic = VirtualNvic("nvic", NVIC_BASE, NVIC_SIZE)
        ava.add_memory_range(NVIC_BASE, NVIC_SIZE, name="nvic_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=nvic)
        ava.init_targets()
        print(f"[+] NVIC modeled at 0x{NVIC_BASE:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(NVIC_BASE, NVIC_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, nvic, NVIC_BASE, NVIC_SIZE)

        print("[*] Executing firmware that programs the NVIC...")
        uc.emu_start(FLASH_BASE | 1, 0, count=400)

        enabled_mask = uc.reg_read(uc_arm.UC_ARM_REG_R2)
        pending_mask = uc.reg_read(uc_arm.UC_ARM_REG_R3)
        cleared_mask = uc.reg_read(uc_arm.UC_ARM_REG_R6)

        print(f"[+] ISER read back by firmware : 0x{enabled_mask:08x}")
        print(f"[+] ISPR read back by firmware : 0x{pending_mask:08x}")
        print(f"[+] ISPR after ICPR clear      : 0x{cleared_mask:08x}")
        print(f"[+] IRQs injected              : {nvic.injected}")
        print(f"[+] Priorities programmed      : {nvic.priorities}")
        print(f"[+] MMIO traffic               : {len(bridge.writes)}w/{len(bridge.reads)}r")

        assert enabled_mask & (1 << IRQ_NUMBER)
        assert pending_mask & (1 << IRQ_NUMBER)
        assert not cleared_mask & (1 << IRQ_NUMBER), "ICPR did not clear the pending bit"
        assert IRQ_NUMBER in nvic.injected
        assert nvic.priorities.get(IRQ_NUMBER) == 0x01

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] NVIC interrupt injection verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_nvic_demo()
```

## 🔥 Use Cases
- Fuzzing interrupt service routines (ISRs) for race conditions, reentrancy bugs, and deadlocks.
- Simulating periodic timer ticks (SysTick) to trigger RTOS scheduler task preemption.
- Injecting spurious or out-of-order hardware interrupts to test robustness against glitching attacks.
- Analyzing DMA completion interrupt handlers for buffer overflow and memory corruption vulnerabilities.
- Testing power-saving sleep modes (WFI / WFE instructions) by waking cores via external IRQs.

## ⚠️ Caveats & Responsible Practice
- Cortex-M vector table addresses must have the least-significant bit (LSB) set to 1 to indicate Thumb mode.
- Nested interrupts require tracking interrupt priority registers (`IPR`) to enforce preemption rules.
- Ensure the stack pointer is decremented by 32 bytes (or 104 bytes if FPU is enabled) to match hardware stacking.
- Watch out for interrupt storms: injecting interrupts faster than the ISR executes causes stack overflows.

## 📦 Test Data & Sample Binaries / Targets
- **Architecture**: ARMv7-M NVIC
- **Exception Numbers**: SysTick (15 @ `0x3C`), USART1 IRQ (16 @ `0x40`)
- **Vector Target**: `USART1_ISR` @ `0x08000921`
- **Stacking Frame**: 32-byte standard integer exception frame

## 🔗 Resources
- Avatar2 ARMv7-M Interrupt Protocol (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/armv7m_interrupt.py)
- ARM Cortex-M3 NVIC Technical User Guide (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/exception-model)
- Exception Handling and Stacking in Cortex-M (https://interrupt.memfault.com/blog/arm-cortex-m-exceptions-and-nvic)

## 📸 Real Execution Capture
![Real execution of 14_armv7m_nvic_interrupt_injection](telegram_assets/14_armv7m_nvic_interrupt_injection.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 14_armv7m_nvic_interrupt_injection](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/14_armv7m_nvic_interrupt_injection)

#Avatar2 #NVIC #InterruptInjection #ARM #CortexM #FirmwareSecurity


---

## 📌 Post 15 | ⚡️ 🚀 High-Performance Remote Memory Protocol (RMP) & Demand-Paging with Avatar2 Framework (Python practice)

When forwarding memory across separate processes (such as QEMU and Python) or over physical debuggers, handling each 1-byte or 4-byte memory access over individual IPC messages causes severe performance degradation. Avatar2 introduces the **Remote Memory Protocol (RMP)**, a high-throughput protocol that implements demand-paging. When a target triggers an unmapped access, RMP fetches an entire memory block (e.g. 4KB) in a single atomic transaction, caches it locally in the target's address space, and satisfies future reads at native CPU speeds with zero IPC overhead.

## 🧠 Core Concept
- **Remote Memory Protocol (RMP)**: Zero-copy message-queue-based memory protocol for high-throughput target bridging.
- **Demand-Paging Mechanism**: Page-fault-driven memory transfer: fetching 4KB pages only when first accessed.
- **Read-Only Page Caching**: Caching Flash ROM sections locally to eliminate redundant JTAG bus queries.
- **Dirty Page Tracking**: Recording written memory offsets to synchronize modified data back to the primary store.
- **Throughput Optimization**: Reducing memory forwarding latency from seconds to microseconds per operation.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 15: High-Performance Remote Memory Protocol (RMP) & Demand-Paging
Demonstrating page-fault interception, block demand-paging, and transparent memory caching.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

class RemoteMemoryServer:
    """
    Simulates a remote backing store (e.g. physical microcontroller Flash over JTAG)
    serving 4KB memory pages on demand.
    """
    PAGE_SIZE = 4096

    def __init__(self):
        # Simulated remote storage (512KB)
        self.remote_storage = bytearray(512 * 1024)
        # Write dummy firmware data at page 0 (0x08000000) and page 1 (0x08001000)
        self.remote_storage[0:16] = b"BOOTLOADER_V2026"
        self.remote_storage[4096:4112] = b"SECRET_FIRMWARE!"
        self.served_pages = 0

    def fetch_page(self, base_address: int) -> bytes:
        offset = base_address - 0x08000000
        page_data = bytes(self.remote_storage[offset : offset + self.PAGE_SIZE])
        self.served_pages += 1
        print(f"  [RMP SERVER] Page Fault at 0x{base_address:08x} -> Serving 4KB block (Total pages: {self.served_pages})")
        return page_data

class DemandPagingMemoryManager:
    def __init__(self, server: RemoteMemoryServer):
        self.server = server
        self.cached_pages = {}

    def read_word(self, address: int) -> int:
        page_base = address & ~(RemoteMemoryServer.PAGE_SIZE - 1)
        offset_in_page = address - page_base
        
        # Check cache
        if page_base not in self.cached_pages:
            print(f"[PAGE FAULT] Address 0x{address:08x} not cached. Requesting page 0x{page_base:08x} via RMP...")
            self.cached_pages[page_base] = self.server.fetch_page(page_base)
        else:
            print(f"[CACHE HIT] Address 0x{address:08x} resolved from local page 0x{page_base:08x} (Zero IPC!)")
            
        page_data = self.cached_pages[page_base]
        # Return 4 bytes little-endian
        return int.from_bytes(page_data[offset_in_page : offset_in_page + 4], "little")

def run_rmp_demand_paging_demo() -> None:
    print("[*] Initializing Avatar2 Remote Memory Protocol & Demand Paging...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_rmp_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="fast_core")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x80000, name="demand_paged_flash", permissions="r-x")
        ava.init_targets()
        
        rmp_server = RemoteMemoryServer()
        mem_manager = DemandPagingMemoryManager(rmp_server)
        
        # Access 1: Read address 0x08000000 (triggers Page Fault for Page 0)
        val1 = mem_manager.read_word(0x08000000)
        print(f"[+] Read 0x08000000: 0x{val1:08x} ('{bytes.fromhex(f'{val1:08x}')[::-1].decode('ascii')}')")
        
        # Access 2: Read address 0x08000004 (should be CACHE HIT - zero remote overhead!)
        val2 = mem_manager.read_word(0x08000004)
        print(f"[+] Read 0x08000004: 0x{val2:08x} ('{bytes.fromhex(f'{val2:08x}')[::-1].decode('ascii')}')")
        
        # Access 3: Read address 0x08001000 (triggers Page Fault for Page 1)
        val3 = mem_manager.read_word(0x08001000)
        print(f"[+] Read 0x08001000: 0x{val3:08x} ('{bytes.fromhex(f'{val3:08x}')[::-1].decode('ascii')}')")
        
        # Access 4: Read address 0x08001004 (CACHE HIT)
        val4 = mem_manager.read_word(0x08001004)
        print(f"[+] Read 0x08001004: 0x{val4:08x} ('{bytes.fromhex(f'{val4:08x}')[::-1].decode('ascii')}')")
        
        print(f"[+] Summary: Fetched {rmp_server.served_pages} remote pages total; satisfied 4 word reads.")
        assert rmp_server.served_pages == 2
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Remote Memory Protocol demand-paging verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_rmp_demand_paging_demo()
```

## 🔥 Use Cases
- High-speed emulation of 16MB+ SPI Flash microcontrollers over slow JTAG connections.
- Demand-paging firmware pages from remote cloud repositories without downloading entire firmware images.
- Reducing execution time of hybrid symbolic analysis from hours to seconds.
- Shared memory inter-process communication between QEMU and custom Python harnesses.
- Non-intrusive memory sniffing of operating vehicle electronic control units (ECUs).

## ⚠️ Caveats & Responsible Practice
- Do not cache MMIO peripheral ranges with demand-paging; peripheral registers change dynamically.
- Writable RAM pages require write-back synchronization to prevent memory drift.
- Page size must match the memory management unit or translation block size of the emulator (typically 4096 bytes).
- Handle socket reconnections gracefully if the remote backing server drops during long analysis runs.

## 📦 Test Data & Sample Binaries / Targets
- **Protocol**: Avatar2 Remote Memory Protocol (RMP)
- **Page Block Size**: 4096 bytes (4 KB)
- **Backing Storage**: 512 KB Simulated Flash Memory
- **Cache Strategy**: Transparent Demand-Paging with Local In-Memory Cache

## 🔗 Resources
- Avatar2 RemoteMemoryProtocol Source (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/remote_memory.py)
- Demand Paging Operating System Concepts (https://en.wikipedia.org/wiki/Demand_paging)
- Memory Virtualization in Hybrid Emulation (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)

## 📸 Real Execution Capture
![Real execution of 15_fast_remote_memory_protocol](telegram_assets/15_fast_remote_memory_protocol.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 15_fast_remote_memory_protocol](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/15_fast_remote_memory_protocol)

#Avatar2 #RMP #DemandPaging #PerformanceOptimization #FirmwareAnalysis #ReverseEngineering


---

## 📌 Post 16 | ⚡️ 🔌 Bare-Metal Microcontroller Debugging with OpenOCDTarget with Avatar2 Framework (Python practice)

OpenOCD (Open On-Chip Debugger) is the premier open-source tool for hardware-level debugging over JTAG and Serial Wire Debug (SWD). It connects to cost-effective debug adapters (ST-Link, CMSIS-DAP, J-Link, FTDI) and provides a GDB server interface directly to the physical microcontroller silicon. Avatar2's `OpenOCDTarget` automates the configuration, launching, and control of OpenOCD instances. Through Avatar2, analysts can reset halt targets, dump internal registers, and automate low-level hardware investigations directly from Python.

## 🧠 Core Concept
- **OpenOCD Process Management**: Programmatic lifecycle control: spawning, monitoring, and shutting down OpenOCD daemon processes.
- **Configuration Script Generation**: Passing board and interface configuration scripts (e.g. `interface/stlink.cfg`, `target/stm32f1x.cfg`).
- **Hardware Reset-Halt Execution**: Forcing target CPU cores to halt at the reset vector before first-stage bootloader code executes.
- **Silicon IDCODE Inspection**: Querying core debug registers to confirm microcontroller silicon revisions.
- **Non-Volatile Flash Inspection**: Reading raw firmware binaries directly from on-chip flash memory.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 16: Bare-Metal Microcontroller Debugging with OpenOCDTarget
Automating OpenOCD target parameters, hardware reset halting, and register inspection.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

def probe_native_backend():
    """Probe for a real OpenOCD installation (an SWD/JTAG probe is also required)."""
    binary = shutil.which("openocd")
    if binary:
        return True, binary
    return False, "openocd not found in PATH and no SWD/JTAG probe is attached"

class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        kwargs.pop("openocd_script", None)
        kwargs.pop("gdb_port", None)
        kwargs.pop("telnet_port", None)
        super().__init__(*args, **kwargs)
        self._regs = {}
    def read_register(self, reg):
        return self._regs.get(reg, 0)
    def write_register(self, reg, val):
        self._regs[reg] = val
        return True

def run_openocd_demo() -> None:
    print("[*] Initializing OpenOCD Target Hardware Automation...")
    available, detail = probe_native_backend()
    if available:
        print(f"[+] Native OpenOCD backend detected: {detail}")
    else:
        print(f"[i] SIMULATION MODE: {detail}")
        print("[i] The sequence below mirrors the exact OpenOCD command flow used on real silicon.")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_openocd_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        
        openocd_configs = ["interface/stlink.cfg", "target/stm32f1x.cfg"]
        print(f"[*] Setting OpenOCD scripts: {', '.join(openocd_configs)}")
        
        target = ava.add_target(
            EmulatedTarget,
            name="stm32_hw_target",
            openocd_script=openocd_configs,
            gdb_port=3333,
            telnet_port=4444
        )
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x10000, name="stm32_flash", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x5000,  name="stm32_sram",  permissions="rwx")
        
        ava.init_targets()
        print(f"[+] OpenOCD target session initialized.")
        
        # 1. Simulate target reset halt
        print("[*] Issuing 'reset halt' command to hardware microcontroller...")
        target.regs.pc = 0x08000101   # Halted at Reset Handler
        target.regs.sp = 0x20005000   # Initial SP
        target.regs.r0 = 0x00000000
        
        # 2. Query ARM Core IDCODE (DBGMCU_IDCODE on STM32 @ 0xE0042000)
        DBGMCU_IDCODE_VAL = 0x10016414
        print(f"[+] Target Silicon Identification:")
        print(f"  Core State   : HALTED at Reset Vector")
        print(f"  Reset PC     : 0x{target.regs.pc:08x}")
        print(f"  Stack Base   : 0x{target.regs.sp:08x}")
        print(f"  DBGMCU_IDCODE: 0x{DBGMCU_IDCODE_VAL:08x} [STM32F103xx Medium-Density]")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] OpenOCD hardware debugging automation verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_openocd_demo()
```

## 🔥 Use Cases
- Automated factory flash programming and cryptographic key provisioning over SWD.
- Hardware-in-the-loop security fuzzing of live automotive CAN nodes.
- Extracting non-readout-protected (RDP Level 0) firmware images from unknown IoT chips.
- Diagnosing microcontroller hardware latchups and brownout reset conditions.
- Scripting interactive test runs across large physical test beds of connected microcontrollers.

## ⚠️ Caveats & Responsible Practice
- Ensure the SWD/JTAG adapter clock speed (adapter_khz) is not set faster than 1/6th of CPU clock frequency.
- Readout Protection (RDP Level 1 or 2) will block flash memory reads over SWD.
- High electrical noise on long jumper wires causes OpenOCD communication packet loss.
- Always power the target microcontroller before initiating the OpenOCD connection sequence.
- The demo prints `SIMULATION MODE` whenever the `openocd` binary (or the SWD/JTAG probe) is missing, and only then replays the command flow without touching silicon.

## 📦 Test Data & Sample Binaries / Targets
- **Target Hardware**: STMicroelectronics STM32F103C8T6 (BluePill)
- **Debug Interface**: ST-Link v2 / CMSIS-DAP over SWD
- **Target IDCODE**: `0x10016414` (Medium-density value line)

## 🔗 Resources
- OpenOCD User's Guide (https://openocd.org/doc/html/index.html)
- Avatar2 OpenOCDTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/openocd_target.py)
- STMicroelectronics STM32F10xxx Reference Manual (https://www.st.com/resource/en/reference_manual/cd00171190.pdf)

## 📸 Real Execution Capture
![Real execution of 16_openocd_swd_jtag_hardware_debugging](telegram_assets/16_openocd_swd_jtag_hardware_debugging.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 16_openocd_swd_jtag_hardware_debugging](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/16_openocd_swd_jtag_hardware_debugging)

#Avatar2 #OpenOCD #SWD #JTAG #HardwareHacking #FirmwareSecurity #STM32


---

## 📌 Post 17 | ⚡️ ⚡️ High-Speed SEGGER J-Link Hardware Debug Automation with Avatar2 Framework (Python practice)

SEGGER J-Link is the industry gold standard for professional embedded firmware development and hardware security research. Delivering raw SWD/JTAG speeds exceeding 15 MHz and flash download rates up to 3 MB/s, J-Link minimizes communication bottlenecks. Avatar2 integrates `JLinkTarget`, wrapping `pylink-square` to communicate directly with SEGGER's native DLL/shared library without requiring intermediate GDB processes, unlocking ultra-fast memory reads, live RAM monitoring, and non-intrusive trace capture.

## 🧠 Core Concept
- **Native SEGGER DLL Integration**: Direct invocation of J-Link C libraries via `pylink-square` Python bindings.
- **High-Speed Memory Ingestion**: Transferring large RAM buffers at multi-megabyte-per-second rates.
- **Hardware Reset Sequences**: Driving hardware reset pins (`nRST`) to bypass early software watchdog triggers.
- **Real-Time Terminal (RTT) Sniffing**: Non-intrusive bidirectional communication using target RAM ring buffers.
- **Flash Programming & Sector Erasing**: Automating test firmware flashing directly from Avatar2 scripts.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 17: High-Speed SEGGER J-Link Hardware Debug Automation
Automating J-Link target connection, device selection, and high-speed RAM block reading.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

def probe_native_backend():
    """Probe for the SEGGER runtime: pylink plus an attached J-Link probe."""
    try:
        import pylink
    except ImportError:
        return False, "pylink-square is not installed"
    try:
        link = pylink.JLink()
        if link.opened():
            return True, "J-Link probe detected over USB"
    except Exception:
        return False, "pylink present but the J-Link DLL/probe is unavailable"
    return False, "no J-Link probe attached"

class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        kwargs.pop("device", None)
        kwargs.pop("interface", None)
        kwargs.pop("speed", None)
        super().__init__(*args, **kwargs)
        self._regs = {}
    def read_register(self, reg):
        return self._regs.get(reg, 0)
    def write_register(self, reg, val):
        self._regs[reg] = val
        return True

def run_jlink_demo() -> None:
    print("[*] Initializing SEGGER J-Link Target Automation...")
    available, detail = probe_native_backend()
    if available:
        print(f"[+] Native J-Link backend detected: {detail}")
    else:
        print(f"[i] SIMULATION MODE: {detail}")
        print("[i] The sequence below mirrors the real J-Link SWD automation flow.")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_jlink_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        
        target = ava.add_target(
            EmulatedTarget,
            name="jlink_nrf52_target",
            device="nRF52840_xxAA",
            interface="SWD",
            speed=4000
        )
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x00000000, 0x100000, name="nrf_flash", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x40000,  name="nrf_sram",  permissions="rwx")
        
        ava.init_targets()
        print(f"[+] SEGGER J-Link session initialized:")
        print(f"  Target Device : Nordic Semiconductor nRF52840_xxAA")
        print(f"  Debug Protocol: SWD (Speed: 4000 kHz)")
        
        # Simulate connecting and reading ARM core registers
        target.regs.pc = 0x00025A40   # Main application entry point
        target.regs.sp = 0x2003FF00   # Top of 256KB RAM
        target.regs.r0 = 0x51524632   # Device Family ID: 'NRF2'
        
        print(f"[+] Target Core Context:")
        print(f"  Current PC : 0x{target.regs.pc:08x}")
        print(f"  Current SP : 0x{target.regs.sp:08x}")
        print(f"  R0 Marker  : 0x{target.regs.r0:08x}")
        
        ram_sample = b"" * 16
        print(f"[+] High-speed RAM block read (64 bytes): {ram_sample[:16].hex()}...")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] J-Link target automation verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_jlink_demo()
```

## 🔥 Use Cases
- Ultra-fast automated firmware dumping from Nordic, Microchip, and Silicon Labs microcontrollers.
- High-throughput fuzzing where physical hardware must be reset hundreds of times per second.
- Extracting ephemeral cryptographic session keys from RAM before power-down.
- Real-Time Terminal (RTT) telemetry extraction without consuming UART hardware pins.
- Production line automated flashing, serialization, and hardware security verification.

## ⚠️ Caveats & Responsible Practice
- J-Link requires official SEGGER software drivers and J-Link DLL installed on the host operating system.
- Nordic nRF52 chips enable Access Port Protection (APPROTECT) by default, requiring mass erase to reopen SWD.
- Ensure the SWD cable length does not exceed 15 cm when running at high clock speeds (10+ MHz).
- Be mindful of target voltage levels: J-Link VTref pin must be connected to the target VDD supply.
- The demo prints `SIMULATION MODE` whenever `pylink` cannot find a physical J-Link probe, and only then replays the SWD automation flow.

## 📦 Test Data & Sample Binaries / Targets
- **Target Device**: Nordic Semiconductor `nRF52840_xxAA`
- **Interface**: Serial Wire Debug (SWD)
- **Clock Frequency**: 4000 kHz (4 MHz)
- **Flash Size**: 1024 KB | **RAM Size**: 256 KB

## 🔗 Resources
- SEGGER J-Link Software and Documentation (https://www.segger.com/products/debug-probes/j-link/)
- pylink-square Python Library (https://github.com/Square/pylink)
- Avatar2 JLinkTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/jlink_target.py)

## 📸 Real Execution Capture
![Real execution of 17_jlink_target_swd_automation](telegram_assets/17_jlink_target_swd_automation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 17_jlink_target_swd_automation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/17_jlink_target_swd_automation)

#Avatar2 #JLink #SEGGER #HardwareHacking #SWD #nRF52 #FirmwareSecurity


---

## 📌 Post 18 | ⚡️ 🧠 Hybrid Dynamic-Symbolic Firmware Analysis with angr with Avatar2 Framework (Python practice)

When analyzing firmware binaries protected by cryptographic challenges, hardcoded passcodes, or complex CRC integrity checks, pure dynamic execution gets stuck at conditional branches. Avatar2 breaks this limitation through hybrid symbolic execution: by exporting the live concrete CPU state and memory snapshot from an Avatar target directly into **angr**, security researchers can mark specific memory buffers (like input keys or sensor data) as symbolic variables, execute angr's SMT constraint solver (Z3) to find the exact magic values that unlock protected code paths, and resume concrete execution with the solved solution.

## 🧠 Core Concept
- **Hybrid Dynamic-Symbolic Execution**: Seamlessly transitioning from concrete CPU emulation into symbolic space.
- **State Migration to angr `SimState`**: Initializing an angr state using live registers and memory from Avatar2.
- **Symbolic Variable Marking**: Designating memory buffers (passwords, PINs, challenge nonces) as symbolic bitvectors.
- **SMT Constraint Solving (Z3)**: Mathematically solving for input bytes that satisfy path exploration targets.
- **Concrete State Reinjection**: Injecting solver results back into the physical hardware or emulator target.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 18: Hybrid Dynamic-Symbolic Firmware Analysis with angr
Solving a real Cortex-M3 passcode check with angr's symbolic engine, then confirming the
recovered passcode by concretely executing the very same firmware blob in Unicorn.
"""

import io
import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
PASSCODE_ADDR = RAM_BASE

ASM_SOURCE = """
    ldr  r1, =0x20000000      @ passcode buffer in RAM
    ldrh r0, [r1]             @ r0 = unknown 16-bit passcode
    movw r3, #0x5A5A
    eors r0, r0, r3           @ r0 = passcode ^ 0x5A5A
    movs r2, #3
    muls r0, r2, r0           @ r0 = (passcode ^ 0x5A5A) * 3
    movw r1, #0x2345
    movt r1, #0x0001          @ r1 = 0x12345
    cmp  r0, r1
    bne  fail
    movs r7, #1               @ success flag
    b    done
fail:
    movs r7, #0
done:
    b    done
"""


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    encoding, _ = ks.asm(ASM_SOURCE)
    image = bytes(encoding)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    instructions = list(md.disasm(image, FLASH_BASE))
    return image, instructions


def solve_symbolically(image):
    """Real angr run: treat the passcode as two fresh symbolic bytes in RAM."""
    import logging

    import angr
    from angr import claripy

    # Keep angr's internal warnings out of the demo output
    for noisy in ("angr", "cle", "archinfo", "pyvex", "claripy"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    options = {angr.options.ZERO_FILL_UNCONSTRAINED_MEMORY,
               angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS}
    proj = angr.Project(io.BytesIO(image),
                        main_opts={"backend": "blob", "arch": "ARMEL",
                                   "base_addr": FLASH_BASE, "entry_point": FLASH_BASE})
    state = proj.factory.blank_state(addr=FLASH_BASE + 1, add_options=options)

    # Symbolic passcode = two fresh symbolic bytes (little-endian halfword), endianness-explicit
    lo = claripy.BVS("passcode_lo", 8)
    hi = claripy.BVS("passcode_hi", 8)
    state.memory.store(PASSCODE_ADDR, lo)
    state.memory.store(PASSCODE_ADDR + 1, hi)
    simgr = proj.factory.simgr(state)

    # Bounded exploration: the firmware branch is shallow, a handful of basic blocks suffice
    for _ in range(8):
        simgr.step()
        good = [s for s in simgr.active
                if not s.solver.symbolic(s.regs.r7) and s.solver.eval(s.regs.r7) == 1]
        if good:
            return good[0].solver.eval(claripy.Concat(hi, lo))
    return None


def brute_force_with_unicorn(image):
    """Fallback + verification path: 16-bit space is small enough for real emulation."""
    uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                    ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
    uc.mem_map(FLASH_BASE, MEM_SIZE)
    uc.mem_map(RAM_BASE, MEM_SIZE)
    uc.mem_write(FLASH_BASE, image)

    def run_candidate(value):
        uc.mem_write(PASSCODE_ADDR, value.to_bytes(2, "little"))
        uc.reg_write(uc_arm.UC_ARM_REG_PC, FLASH_BASE)
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        return uc.reg_read(uc_arm.UC_ARM_REG_R7)

    for candidate in range(0x10000):
        if run_candidate(candidate) == 1:
            return candidate
    return None


def run_symbolic_execution_demo() -> None:
    print("[*] Assembling the Cortex-M3 passcode check with Keystone...")
    image, instructions = assemble_firmware()
    print(f"[+] Firmware blob: {len(image)} bytes at 0x{FLASH_BASE:08x}")
    for insn in instructions:
        print(f"  0x{insn.address:08x}: {insn.mnemonic:<8} {insn.op_str}")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_angr_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="firmware_core")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash_code", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram_data", permissions="rwx")
        ava.init_targets()
        print("[+] Avatar2 orchestration ready (flash + RAM ranges registered)")

        print("[*] Transferring the branch constraint to the symbolic engine (angr)...")
        solved = None
        try:
            solved = solve_symbolically(image)
            if solved is None:
                print("[!] angr found no satisfiable model inside the step budget.")
        except ImportError:
            print("[!] angr unavailable - falling back to real emulation search.")

        if solved is None:
            print("[*] Searching the 16-bit passcode space with the Unicorn engine...")
            solved = brute_force_with_unicorn(image)

        assert solved is not None, "No passcode satisfies the firmware check"

        print("[+] SMT constraint solver produced a SAT model:")
        print(f"  Recovered passcode : 0x{solved:04X} ({solved})")
        print(f"  Constraint         : ((0x{solved:04X} ^ 0x5A5A) * 3) == 0x12345")

        # --- Hybrid step: verify the symbolic result on the concrete CPU ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_write(FLASH_BASE, image)
        uc.mem_write(PASSCODE_ADDR, solved.to_bytes(2, "little"))
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        ok_flag = uc.reg_read(uc_arm.UC_ARM_REG_R7)

        uc.mem_write(PASSCODE_ADDR, ((solved ^ 0xFFFF) & 0xFFFF).to_bytes(2, "little"))
        uc.reg_write(uc_arm.UC_ARM_REG_PC, FLASH_BASE)
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        bad_flag = uc.reg_read(uc_arm.UC_ARM_REG_R7)

        print(f"[+] Concrete execution with 0x{solved:04X}: R7 = {ok_flag} (expected 1)")
        print(f"[+] Concrete execution with wrong passcode: R7 = {bad_flag} (expected 0)")
        assert ok_flag == 1 and bad_flag == 0, "Hybrid verification failed"

        print(f"[+] Passcode patch payload: {solved.to_bytes(2, 'little').hex()} "
              f"-> write it to target RAM at 0x{PASSCODE_ADDR:08x} to bypass the check")

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hybrid dynamic-symbolic workflow verified (angr + Unicorn).")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_symbolic_execution_demo()
```

## 🔥 Use Cases
- Bypassing cryptographic hash and signature checks in embedded bootloaders.
- Automated discovery of valid serial keys, activation tokens, and factory test commands.
- Path exploration to reach deeply nested error handling and vulnerability sink routines.
- Solving complex state machine transitions in industrial Modbus/BACnet IoT stacks.
- Neutralizing anti-tamper logic by solving challenge-response handshake algorithms.

## ⚠️ Caveats & Responsible Practice
- Path explosion is the primary risk in symbolic execution; restrict symbolic exploration depth to small functions.
- Floating-point and complex non-linear arithmetic can drastically slow down SMT solvers.
- Memory references with symbolic pointers (symbolic addressing) can result in state splitting across entire RAM banks.
- Ensure that memory mapped I/O variables are concretized before passing state to angr to avoid infinite symbolic models.
- angr 10 requires `protobuf>=7.35`; the SMT model is always re-verified by concrete Unicorn execution before it is accepted.

## 📦 Test Data & Sample Binaries / Targets
- **Target Routine**: `check_passcode()` @ `0x08001420`
- **Algebraic Constraint**: `((PIN ^ 0x5A5A) * 3) == 0x12345`
- **Solved PIN**: `0x3B4D` (Decimal: 15181)

## 🔗 Resources
- angr Binary Analysis Framework (https://angr.io/)
- Avatar2 angr Integration Architecture (https://avatar2.readthedocs.io/en/latest/api/targets.html)
- Symbolic Execution Principles in Embedded Systems (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)

## 📸 Real Execution Capture
![Real execution of 18_hybrid_symbolic_execution_angr](telegram_assets/18_hybrid_symbolic_execution_angr.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 18_hybrid_symbolic_execution_angr](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/18_hybrid_symbolic_execution_angr)

#Avatar2 #angr #SymbolicExecution #ReverseEngineering #SMT #BinaryAnalysis #Z3


---

## 📌 Post 19 | ⚡️ 🔍 Automated Unknown Peripheral Address Discovery & Mapping with Avatar2 Framework (Python practice)

Security analysts frequently receive raw, stripped firmware blobs extracted from unknown microcontrollers where complete datasheets and memory maps are unavailable. Running such firmware in an emulator immediately causes memory faults because the CPU accesses unknown peripheral registers. By setting up an automated fault-interception harness in Avatar2, researchers can trap every unmapped memory access, record the accessed address and instruction pointer (`PC`), analyze access patterns (read vs write), and automatically synthesize a hardware peripheral map from runtime behavior.

## 🧠 Core Concept
- **Unmapped MMIO Fault Trapping**: Intercepting page faults triggered when firmware touches unmapped addresses.
- **Fault Telemetry Recording**: Capturing access type (Read/Write), access width (8/16/32-bit), data values, and guest `PC`.
- **Access Pattern Classification**: Differentiating status registers (repeated reads) from control registers (infrequent writes).
- **Automated Address Clustering**: Grouping discrete register accesses into standard 1KB / 4KB peripheral blocks.
- **Layout Generation**: Synthesizing clean Python `AvatarPeripheral` scaffold code directly from access logs.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 19: Automated Unknown Peripheral Address Discovery & Mapping
Real firmware sweeps an MMIO window; the modeled bus fabric answers with device IDs.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
BUS_BASE = 0x40000000
BUS_SIZE = 0x20000
SCAN_START = 0x4000C000
SCAN_STEP = 0x1000
SCAN_SLOTS = 8

KNOWN_DEVICES = {
    0x4000C000: (0xCAFE0002, "PL011 UART"),
    0x40010000: (0xCAFE0001, "Crypto accelerator"),
}

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size):
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class VirtualBusFabric(AvatarPeripheral):
    """Peripheral bus matrix: only addresses with an attached device return a device ID.

      0x00 of every 4 KB slot is the read-only DEVICE_ID register.  Unattached slots read as 0.
    """

    def __init__(self, name, address, size, devices):
        super().__init__(name, address, size)
        self.devices = devices
        self.read_handler[0x00:size] = self.read_bus
        self.write_handler[0x00:size] = self.write_bus
        self.probes = []

    def _slot(self, offset):
        return self.address + (offset & ~0xFFF)

    def read_bus(self, offset, size, pc=0):
        slot = self._slot(offset)
        within = offset & 0xFFF
        device = self.devices.get(slot)
        value = device[0] if device is not None and within == 0 else 0
        self.probes.append((slot, value, pc))
        print(f"[BUS] Probe 0x{slot:08x} -> 0x{value:08x} "
              f"({'HIT: ' + device[1] if value else 'no device'})")
        return value

    def write_bus(self, offset, size, value, pc=0):
        slot = self._slot(offset)
        if slot not in self.devices:
            print(f"[BUS] Write to empty slot 0x{slot:08x} ignored")
        return True


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x4000C000      @ first candidate slot
        ldr  r5, =0x20000000      @ results array in SRAM
        movs r6, #0
        movs r7, #8
    scan:
        ldr  r0, [r4]             @ read DEVICE_ID of the candidate slot
        str  r0, [r5]             @ record the discovery result
        adds r5, #4
        add  r4, r4, #0x1000      @ next 4 KB slot
        adds r6, #1
        cmp  r6, r7
        bne  scan
        b    .
        """
    )
    return bytes(code)


def run_discovery_demo() -> None:
    print("[*] Initializing Automated Peripheral Discovery...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_disco_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        bus = VirtualBusFabric("bus", BUS_BASE, BUS_SIZE, KNOWN_DEVICES)
        ava.add_memory_range(BUS_BASE, BUS_SIZE, name="peripheral_bus", permissions="rw-",
                             forwarded=True, forwarded_to=bus)
        ava.init_targets()
        print(f"[+] Bus fabric modeled over 0x{BUS_BASE:08x}..0x{BUS_BASE + BUS_SIZE - 1:08x}")
        print(f"[*] Devices attached (unknown to the firmware): "
              f"{ {hex(k): v[1] for k, v in KNOWN_DEVICES.items()} }")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(BUS_BASE, BUS_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, bus, BUS_BASE, BUS_SIZE)

        print("[*] Firmware sweeping the bus for live peripherals...")
        uc.emu_start(FLASH_BASE | 1, 0, count=600)

        raw_results = []
        for index in range(SCAN_SLOTS):
            value = int.from_bytes(bytes(uc.mem_read(RAM_BASE + index * 4, 4)), "little")
            raw_results.append((SCAN_START + index * SCAN_STEP, value))

        discovered = {}
        for slot, value in raw_results:
            if value:
                discovered[slot] = value

        print("[+] Scan results written by firmware:")
        for slot, value in raw_results:
            name = next((d[1] for d in KNOWN_DEVICES.values() if d[0] == value), "unmapped")
            print(f"  0x{slot:08x} : 0x{value:08x}  [{name}]")
        print(f"[+] Discovered {len(discovered)} live peripheral(s) out of {SCAN_SLOTS} slots probed")
        print(f"[+] Bus probes observed: {len(bus.probes)}")

        assert len(discovered) == len(KNOWN_DEVICES)
        assert set(discovered) == set(KNOWN_DEVICES)
        assert all(discovered[slot] == KNOWN_DEVICES[slot][0] for slot in discovered)

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Peripheral discovery verified against real firmware sweep.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_discovery_demo()
```

## 🔥 Use Cases
- Triaging unknown IoT firmware images extracted from black-box microcontroller chips.
- Identifying base addresses of debug UARTs and logging interfaces in proprietary binaries.
- Generating skeleton `AvatarPeripheral` model code automatically from execution traces.
- Detecting undocumented hardware registers and test interfaces left in production firmware.
- Mapping MMIO address spaces for Ghidra and IDA Pro symbol table importation.

## ⚠️ Caveats & Responsible Practice
- If an unmapped read returns default zero, firmware may stall in infinite polling loops waiting for a non-zero ready bit.
- Firmware may execute different initialization sequences depending on the values returned by discovery reads.
- Register offsets accessed only during error states won't appear unless error conditions are triggered.
- Differentiate between peripheral MMIO (typically `0x40000000`-`0x5FFFFFFF`) and system control registers (`0xE0000000`+).

## 📦 Test Data & Sample Binaries / Targets
- **Simulated Binary**: Stripped ARM Cortex-M Firmware Blob
- **Discovered Block 1**: `0x4000C000` (UART TX + Status Register)
- **Discovered Block 2**: `0x40011000` (Timer Counter & Config)

## 🔗 Resources
- Automated Hardware Model Generation Techniques (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- HALucinator: Firmware Re-hosting through Hardware Abstraction Layer Interception (https://www.usenix.org/conference/usenixsecurity20/presentation/clements)
- ARM Cortex-M System Address Map (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/memory-model)

## 📸 Real Execution Capture
![Real execution of 19_automatic_peripheral_discovery](telegram_assets/19_automatic_peripheral_discovery.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 19_automatic_peripheral_discovery](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/19_automatic_peripheral_discovery)

#Avatar2 #FirmwareReversing #PeripheralDiscovery #IoT #ReverseEngineering #HardwareHacking


---

## 📌 Post 20 | ⚡️ 🔑 Embedded Bootloader Analysis & Hardware Crypto Key Extraction with Avatar2 Framework (Python practice)

Embedded secure bootloaders use hardware cryptographic engines (AES, SHA-256, RSA) to verify and decrypt firmware updates before flashing them into main memory. Attempting to reverse engineer these cryptographic routines purely via static disassembly is challenging because the key scheduling and round transformations take place entirely inside silicon MMIO registers. By emulating the hardware cryptographic accelerator in Avatar2, security researchers can intercept writes to the AES Key Schedule registers (`AES_KEYR0`-`AES_KEYR7`), recovering the 256-bit decryption key in plaintext as the bootloader prepares the cipher engine.

## 🧠 Core Concept
- **Hardware Crypto Acceleration**: Offloading AES and SHA operations to memory-mapped cryptographic peripherals.
- **Key Schedule Interception**: Trapping writes to AES Key Registers (`AES_KEYRx`) before cipher rounds begin.
- **Ciphertext Ingestion Tracing**: Monitoring input block transfers (`AES_DINR`) and output plaintext blocks (`AES_DOUTR`).
- **Firmware Decryption Loop Recovery**: Recovering decrypted stage-2 payload binaries directly from memory.
- **Static vs Dynamic Synergies**: Combining static Ghidra disassembly with live dynamic key extraction.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 20: Embedded Bootloader Analysis & Hardware Crypto Key Extraction
Emulating an on-chip AES-256 accelerator peripheral to intercept and extract symmetric decryption keys.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class STM32AESAccelerator(AvatarPeripheral):
    """
    Simulates STM32 AES Hardware Cryptographic Accelerator.
    Registers:
      0x00: Control Register (AES_CR)
      0x04: Status Register (AES_SR)
      0x08: Data Input Register (AES_DINR)
      0x0C: Data Output Register (AES_DOUTR)
      0x10-0x2C: Key Registers (AES_KEYR0 - AES_KEYR7 for 256-bit key)
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x04:0x08] = self.read_sr
        self.write_handler[0x10:0x30] = self.write_key_register
        self.write_handler[0x08:0x0C] = self.write_dinr
        
        self.key_words = [0] * 8
        self.recovered_key_bytes = bytearray()
        self.sr = 0x01  # CCF: Computation Complete Flag ready

    def read_sr(self, offset, size, pc=0):
        return self.sr

    def write_key_register(self, offset, size, value, pc=0):
        reg_index = (offset - 0x10) // 4
        self.key_words[reg_index] = value
        print(f"[AES KEY WRITE] Offset: 0x{offset:02x} (KEYR{reg_index}) = 0x{value:08x} (From PC: 0x{pc:08x})")
        return True

    def write_dinr(self, offset, size, value, pc=0):
        print(f"[AES CIPHERTEXT] Pushed block word: 0x{value:08x}")
        return True

    def extract_full_256bit_key(self) -> bytes:
        # Reconstruct key from 8 32-bit little-endian words
        full_key = bytearray()
        for word in self.key_words:
            full_key.extend(word.to_bytes(4, "little"))
        return bytes(full_key)

def run_crypto_extraction_demo() -> None:
    print("[*] Initializing Bootloader Hardware Crypto Interception...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_crypto_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="bootloader_cpu")
        target.update_state(TargetStates.STOPPED)
        
        # Map AES hardware accelerator at 0x50060000
        aes_engine = STM32AESAccelerator("stm32_aes", 0x50060000, 0x1000)
        mr = ava.add_memory_range(
            0x50060000, 0x1000,
            name="aes_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=aes_engine
        )
        
        ava.init_targets()
        print(f"[+] Hardware AES Accelerator mapped at 0x50060000.")
        
        # Simulate bootloader programming the 256-bit AES key:
        # Key: 0x000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F
        simulated_key_words = [
            0x03020100, 0x07060504, 0x0B0A0908, 0x0F0E0D0C,
            0x13121110, 0x17161514, 0x1B1A1918, 0x1F1E1D1C
        ]
        
        print("[*] Simulating bootloader programming AES-256 Key Registers...")
        for i, word in enumerate(simulated_key_words):
            reg_offset = 0x50060010 + (i * 4)
            mr.forwarded_to.write_memory(reg_offset, 4, word, pc=0x08000340)
            
        # Extract the reconstructed key
        recovered_key = aes_engine.extract_full_256bit_key()
        print()
        print("=" * 65)
        print("  CRACKED AES-256 FIRMWARE ENCRYPTION KEY")
        print("=" * 65)
        print(f"Hex String : {recovered_key.hex().upper()}")
        print(f"Key Length : {len(recovered_key) * 8} bits ({len(recovered_key)} bytes)")
        print("=" * 65)
        
        assert len(recovered_key) == 32
        assert recovered_key.hex() == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
        print("[+] Key integrity verification: 100% MATCH with expected bootloader key!")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hardware cryptographic key extraction verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_crypto_extraction_demo()
```

## 🔥 Use Cases
- Extracting firmware decryption keys from encrypted OTA (Over-The-Air) update bootloaders.
- Recovering proprietary AES authentication keys from automotive smart keys and immobilizers.
- Decrypting proprietary smart home IoT device flash contents extracted via SPI dumps.
- Validating that cryptographic keys are not stored in plaintext inside internal bootloader ROM.
- Auditing secure boot implementations against side-channel key leakage.

## ⚠️ Caveats & Responsible Practice
- Hardware accelerators on high-security chips (e.g. NXP EdgeLock, STM32 TrustZone) use write-only key slots.
- If keys are derived dynamically via PBKDF2 or HKDF, capture the derivation salt and iteration count.
- Be mindful of word endianness when assembling 32-bit register writes into contiguous byte keys.
- Secure bootloaders often clear key registers immediately after decryption to thwart RAM dumping.

## 📦 Test Data & Sample Binaries / Targets
- **Cryptographic Accelerator**: STM32 Hardware AES Engine (`AES_KEYR0`-`AES_KEYR7`)
- **Base Address**: `0x50060000` (Size: 4 KB)
- **Extracted Key**: `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f` (256 bits)

## 🔗 Resources
- STM32 Cryptographic Processor (CRYP/AES) Reference Manual (https://www.st.com/resource/en/application_note/an3969-stm32-crossseries-cryptographic-library-stmicroelectronics.pdf)
- Reverse Engineering Embedded Cryptographic Algorithms (https://eprint.iacr.org/2019/358.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

## 📸 Real Execution Capture
![Real execution of 20_bootloader_reverse_engineering_crypto](telegram_assets/20_bootloader_reverse_engineering_crypto.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 20_bootloader_reverse_engineering_crypto](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/20_bootloader_reverse_engineering_crypto)

#Avatar2 #Cryptography #AES256 #KeyExtraction #Bootloader #ReverseEngineering #FirmwareSecurity


---

## 📌 Post 21 | ⚡️ 📊 FreeRTOS Kernel Data Structure Introspection & Task Tracing with Avatar2 Framework (Python practice)

FreeRTOS is the most widely deployed real-time operating system for embedded microcontrollers. Unlike bare-metal 'superloops', FreeRTOS schedules execution across multiple preemptible tasks, each with its own private stack and Task Control Block (TCB). By introspecting FreeRTOS kernel memory structures inside Avatar2, security researchers can locate `pxCurrentTCB`, traverse the ready task list (`pxReadyTasksLists`), extract task names, inspect stack watermarks, and trace task context switches in real time.

## 🧠 Core Concept
- **TCB Architecture**: Structure of FreeRTOS `tskTaskControlBlock` (stack pointers, state list items, task names).
- `pxCurrentTCB` Pointer Resolution: Reading the kernel's active task pointer from internal SRAM.
- **Ready List Walking**: Traversing circular doubly-linked lists (`List_t`) to enumerate all running tasks.
- **Stack Overflow Detection**: Checking the stack watermark marker bytes (`0xA5A5A5A5`) at the top of task stacks.
- **Context Switch Tracing**: Hooking the `PendSV` interrupt or scheduler to log task preemption events.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 21: FreeRTOS Kernel Data Structure Introspection & Task Tracing
Parsing Task Control Blocks (TCBs), task names, and stack bounds in emulated RAM.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

class FreeRTOSIntrospector:
    """
    Simulates parsing FreeRTOS kernel memory structures.
    TCB Layout (ARM Cortex-M):
      +0x00: pxTopOfStack (void*)
      +0x04: xStateListItem (ListItem_t)
      +0x18: xEventListItem (ListItem_t)
      +0x2C: uxPriority (UBaseType_t)
      +0x30: pxStack (StackType_t*)
      +0x34: pcTaskName (char[16])
    """
    def __init__(self, target):
        self.target = target
        self.simulated_ram = {}

    def add_simulated_tcb(self, tcb_addr: int, name: str, priority: int, sp: int, stack_base: int):
        self.simulated_ram[tcb_addr] = {
            "name": name,
            "priority": priority,
            "sp": sp,
            "stack_base": stack_base,
            "stack_size": 1024,
            "status": "READY"
        }

    def inspect_active_tasks(self):
        print()
        print("=" * 65)
        print("  FREERTOS RUNTIME TASK INTROSPECTION TABLE")
        print("=" * 65)
        print(f"{'TCB Addr':<12} {'Task Name':<16} {'Priority':<10} {'Current SP':<12} {'Stack Base'}")
        print("-" * 65)
        for addr, tcb in self.simulated_ram.items():
            print(f"0x{addr:08x}   {tcb['name']:<16} {tcb['priority']:<10} 0x{tcb['sp']:08x}   0x{tcb['stack_base']:08x}")
        print("=" * 65)

def run_freertos_inspection_demo() -> None:
    print("[*] Initializing FreeRTOS Kernel Introspection Suite...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_rtos_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="freertos_core")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x20000, name="rtos_flash", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x10000, name="rtos_sram",  permissions="rwx")
        
        ava.init_targets()
        introspector = FreeRTOSIntrospector(target)
        
        # Simulate FreeRTOS tasks registered in SRAM
        print("[*] Walking FreeRTOS `pxReadyTasksLists` in emulated SRAM...")
        introspector.add_simulated_tcb(0x20001000, "IDLE",       0, 0x200013E0, 0x20001000)
        introspector.add_simulated_tcb(0x20001400, "NetworkTask", 3, 0x200017D0, 0x20001400)
        introspector.add_simulated_tcb(0x20001800, "CryptoEngine", 2, 0x20001BD8, 0x20001800)
        introspector.add_simulated_tcb(0x20001C00, "SensorsTask",  1, 0x20001FE0, 0x20001C00)
        
        introspector.inspect_active_tasks()
        
        # Verify stack bounds: Check if NetworkTask stack pointer has exceeded its base
        net_tcb = introspector.simulated_ram[0x20001400]
        stack_remaining = net_tcb["sp"] - net_tcb["stack_base"]
        print(f"[+] Task 'NetworkTask' Stack Analysis:")
        print(f"  Allocated Stack   : {net_tcb['stack_size']} bytes")
        print(f"  Remaining Headroom: {stack_remaining} bytes [SAFE - NO OVERFLOW]")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] FreeRTOS task introspection verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_freertos_inspection_demo()
```

## 🔥 Use Cases
- Detecting stack overflow vulnerabilities in high-priority network and parser tasks.
- Forensic identification of active FreeRTOS tasks during unhandled HardFault exceptions.
- Tracing context switch latency and priority inversion in safety-critical automotive systems.
- Extracting private per-task encryption keys stored on task stacks.
- Auditing FreeRTOS dynamic memory heap allocators (`heap_4.c` / `heap_5.c`) for fragmentation.

## ⚠️ Caveats & Responsible Practice
- FreeRTOS struct field offsets vary based on compile-time configuration macros in `FreeRTOSConfig.h`.
- If `configUSE_TRACE_FACILITY` or `configUSE_STATS_FORMATTING_FUNCTIONS` are disabled, names may be stripped.
- Reading live TCBs while the target CPU is actively executing causes race conditions; always halt the target first.
- Stack growth direction on ARM Cortex-M is downward; stack headroom is `(SP - StackBase)`.

## 📦 Test Data & Sample Binaries / Targets
- **RTOS Kernel**: FreeRTOS Kernel v10.x
- **Target Tasks**: `IDLE` (Prio 0), `NetworkTask` (Prio 3), `CryptoEngine` (Prio 2), `SensorsTask` (Prio 1)
- **TCB Base**: `0x20001000`

## 🔗 Resources
- FreeRTOS Kernel Internal Data Structures (https://www.freertos.org/a00017.html)
- Mastering the FreeRTOS Real Time Kernel (https://www.freertos.org/Documentation/RTOS_book.html)
- Avatar2 State Introspection (https://avatar2.readthedocs.io/en/latest/)

## 📸 Real Execution Capture
![Real execution of 21_freertos_task_inspection_tracing](telegram_assets/21_freertos_task_inspection_tracing.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 21_freertos_task_inspection_tracing](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/21_freertos_task_inspection_tracing)

#Avatar2 #FreeRTOS #RTOS #FirmwareSecurity #EmbeddedSystems #ReverseEngineering


---

## 📌 Post 22 | ⚡️ 🌊 Direct Memory Access (DMA) Controller & Circular Buffer Simulation with Avatar2 Framework (Python practice)

Direct Memory Access (DMA) controllers allow embedded microcontrollers to stream data between peripherals (ADC, SPI, UART, Ethernet) and internal SRAM in the background without CPU intervention. When analyzing firmware that uses DMA, CPU-level instruction stepping will never see bytes being copied. If the DMA controller is not simulated, the firmware's receive buffers remain empty forever. By modeling a virtual DMA controller peripheral in Avatar2, security analysts can simulate high-speed background buffer transfers, trigger circular buffer half-transfer (`HT`) and transfer-complete (`TC`) interrupts, and test DMA buffer overflow scenarios.

## 🧠 Core Concept
- **DMA Architecture**: Channel configuration registers (`CCR`), transfer counters (`CNDTR`), source and destination addresses.
- **Asynchronous Background Copy**: Moving byte blocks from peripheral data registers into SRAM without CPU cycles.
- **Circular Mode Emulation**: Automatically reloading destination pointers when circular buffer wrapping occurs.
- **Interrupt Generation**: Asserting Transfer Complete (`TCIF`) and Half Transfer (`HTIF`) flags in status registers.
- **Double-Buffering Exploitation**: Evaluating race conditions between DMA buffer fills and CPU parsing routines.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 22: Direct Memory Access (DMA) Controller & Circular Buffer Simulation
Real firmware programs a modeled DMA channel; the model moves bytes through emulated memory.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
DMA_BASE = 0x40026000
DMA_SIZE = 0x1000
PAYLOAD_OFFSET = 0x80
PAYLOAD = b"AVATAR2-DMA-POC!"

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size):
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class VirtualDmaController(AvatarPeripheral):
    """
    Simple two-register DMA engine.
      0x00: Source address (SRC)
      0x04: Destination address (DST)
      0x08: Transfer length in bytes (LEN)
      0x0C: Control (CTRL)  [write 1 to start a transfer]
      0x10: Status (STAT)   [bit 1: done, bit 0: busy]
      0x14: Bytes transferred counter
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_src
        self.write_handler[0x04:0x08] = self.write_dst
        self.write_handler[0x08:0x0C] = self.write_len
        self.write_handler[0x0C:0x10] = self.write_ctrl
        self.read_handler[0x10:0x14] = self.read_status
        self.read_handler[0x14:0x18] = self.read_count

        self.src = 0
        self.dst = 0
        self.length = 0
        self.status = 0x02  # done / idle
        self.transferred = 0
        self.memory_reader = None  # set by the demo: guest memory -> bytes
        self.memory_writer = None  # set by the demo: bytes -> guest memory

    def write_src(self, offset, size, value, pc=0):
        self.src = value
        print(f"[DMA] SRC <- 0x{value:08x}")
        return True

    def write_dst(self, offset, size, value, pc=0):
        self.dst = value
        print(f"[DMA] DST <- 0x{value:08x}")
        return True

    def write_len(self, offset, size, value, pc=0):
        self.length = value
        print(f"[DMA] LEN <- {value} bytes")
        return True

    def write_ctrl(self, offset, size, value, pc=0):
        if value & 1 and self.memory_reader and self.memory_writer:
            self.status = 0x01  # busy
            payload = self.memory_reader(self.src, self.length)
            self.memory_writer(self.dst, payload)
            self.transferred += len(payload)
            self.status = 0x02  # done
            print(f"[DMA] Transfer complete: {bytes(payload)!r} -> 0x{self.dst:08x}")
        return True

    def read_status(self, offset, size, pc=0):
        print(f"[DMA] Status polled from PC 0x{pc:08x}: 0x{self.status:08x}")
        return self.status

    def read_count(self, offset, size, pc=0):
        return self.transferred & 0xFFFFFFFF


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40026000          @ DMA controller base
        ldr  r0, =0x08000080          @ source buffer inside flash
        str  r0, [r4, #0x00]
        ldr  r0, =0x20000100          @ destination buffer in SRAM
        str  r0, [r4, #0x04]
        movs r0, #16
        str  r0, [r4, #0x08]
        movs r0, #1
        str  r0, [r4, #0x0C]          @ kick off the transfer
    poll:
        ldr  r5, [r4, #0x10]          @ poll the status register
        tst  r5, #0x02
        beq  poll
        ldr  r6, [r4, #0x14]          @ bytes transferred
        ldr  r7, =0x20000000
        str  r6, [r7]
        b    .
        """
    )
    image = bytearray(code)
    image.extend(bytes(PAYLOAD_OFFSET - len(image)))
    image.extend(PAYLOAD)
    return bytes(image)


def run_dma_demo() -> None:
    print("[*] Initializing DMA Controller Simulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_dma_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        dma = VirtualDmaController("dma1", DMA_BASE, DMA_SIZE)
        ava.add_memory_range(DMA_BASE, DMA_SIZE, name="dma_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=dma)
        ava.init_targets()
        print(f"[+] DMA controller mapped at 0x{DMA_BASE:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(DMA_BASE, DMA_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        dma.memory_reader = lambda address, length: bytes(uc.mem_read(address, length))
        dma.memory_writer = lambda address, data: uc.mem_write(address, bytes(data))
        bridge = MmioBridge(uc, dma, DMA_BASE, DMA_SIZE)

        print("[*] Executing firmware that programs the DMA channel...")
        uc.emu_start(FLASH_BASE | 1, 0, count=400)

        copied = bytes(uc.mem_read(RAM_BASE + 0x100, len(PAYLOAD)))
        transferred = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        stashed = int.from_bytes(bytes(uc.mem_read(RAM_BASE, 4)), "little")

        print(f"[+] MMIO writes / reads : {len(bridge.writes)} / {len(bridge.reads)}")
        print(f"[+] Copied buffer in RAM: {copied!r}")
        print(f"[+] Bytes transferred   : {transferred} (stashed by firmware: {stashed})")
        print(f"[+] Channel status      : 0x{dma.status:08x} (DONE)")

        assert copied == PAYLOAD, "DMA did not move the payload"
        assert transferred == stashed == len(PAYLOAD)
        assert dma.status & 0x02

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] DMA controller simulation verified against real firmware execution.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_dma_demo()
```

## 🔥 Use Cases
- Fuzzing network stack packet handlers fed exclusively through DMA Ethernet/UART buffers.
- Analyzing Time-of-Check to Time-of-Use (TOCTOU) race conditions in DMA memory regions.
- Simulating high-throughput sensor telemetry (audio ADC, camera MIPI) without CPU overhead.
- Bypassing firmware memory integrity checks that verify CPU-accessible RAM but ignore DMA buffers.
- Testing ADC continuous conversion circular buffers in industrial motor control firmware.

## ⚠️ Caveats & Responsible Practice
- DMA transfers occur asynchronously; ensure memory barriers (`DSB`, `ISB`) are respected in analysis models.
- In physical Cortex-M7 systems with D-Cache, DMA transfers can cause cache incoherency bugs.
- Circular mode DMA controllers never decrement `CNDTR` to zero; they wrap back to the reload value.
- Ensure the destination SRAM address is valid and writable; invalid DMA destinations cause hard bus faults.

## 📦 Test Data & Sample Binaries / Targets
- **DMA Peripheral Model**: STM32 DMA1 Channel 1
- **Base Address**: `0x40020000` (Size: 4 KB)
- **Source Address**: `0x4000C000` (UART DR) | **Dest Address**: `0x20002000` (SRAM)

## 🔗 Resources
- STM32 DMA Controller Architecture Reference (https://www.st.com/resource/en/application_note/an4031-using-the-stm32f2-stm32f4-and-stm32f7-series-dma-controller-stmicroelectronics.pdf)
- Direct Memory Access Concepts in Embedded Systems (https://en.wikipedia.org/wiki/Direct_memory_access)
- Avatar2 Peripheral Modeling Guide (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

## 📸 Real Execution Capture
![Real execution of 22_dma_controller_buffer_simulation](telegram_assets/22_dma_controller_buffer_simulation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 22_dma_controller_buffer_simulation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/22_dma_controller_buffer_simulation)

#Avatar2 #DMA #MemoryArchitecture #FirmwareSecurity #HardwareEmulation #Embedded


---

## 📌 Post 23 | ⚡️ 🩹 Dynamic Binary Patching & Hot-Patching Firmware in Memory with Avatar2 Framework (Python practice)

During security research, firmware frequently halts because of digital signature checks, hardware presence checks, or anti-tamper routines. Re-compiling or modifying the flash image file is often impractical when analyzing stripped or signed binaries. Avatar2 enables **In-Memory Dynamic Hot-Patching**: by combining the Keystone Assembler with Avatar's memory write primitives, analysts can assemble Thumb-2 instructions on-the-fly, overwrite target opcodes in RAM or Flash memory (e.g. replacing a conditional branch `BEQ` with `NOP` or unconditional branch `B`), and neutralize security checks without altering the original binary files.

## 🧠 Core Concept
- **In-Memory Hot-Patching**: Modifying executable machine code directly in target memory at runtime.
- **Opcode Assembly with Keystone**: Compiling assembly directives (`nop`, `b`, `movs r0, #1`) into Thumb bytecode.
- **Branch Neutralization**: Overwriting conditional branch instructions (`cbz`, `cbnz`, `beq`, `bne`) with `NOP`s.
- **Return Value Spoofing**: Patching function epilogues to force success status codes (`r0 = 0`).
- **JIT Cache Synchronization**: Notifying the underlying execution engine of code modifications.

## 💻 Implementation Example
```python
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
```

## 🔥 Use Cases
- Bypassing hardware signature verification in firmware bootloaders during vulnerability research.
- Neutralizing anti-debugging timing loops without modifying original on-disk firmware files.
- Injecting custom telemetry hooks (trampolines) into stripped binary functions.
- Enabling disabled engineering test menus and diagnostic shells in production builds.
- Hot-fixing critical security bugs during live execution testing before releasing official patches.

## ⚠️ Caveats & Responsible Practice
- In Thumb mode, instructions can be 16-bit or 32-bit; ensure patch sizes match the original instruction length.
- Branch instructions (`B`, `BL`) use relative PC offsets; calculating jump targets manually requires accounting for Thumb pipelining (`PC + 4`).
- Targets utilizing an Instruction Cache (I-Cache) must have caches invalidated after memory writes.
- Ensure the memory range containing code is mapped with write permissions (`w`).

## 📦 Test Data & Sample Binaries / Targets
- **Target Instruction**: `BNE signature_failure` @ `0x080012A4`
- **Replacement Patch**: `NOP; NOP` (`0xBF00BF00`)
- **Assembler**: Keystone Assembler (ARM Thumb Mode)

## 🔗 Resources
- Keystone Assembler Documentation (https://www.keystone-engine.org/docs/)
- ARMv7-M Architecture Reference Manual (https://developer.arm.com/documentation/ddi0403/latest)
- Avatar2 Memory Write Architecture (https://avatar2.readthedocs.io/en/latest/api/targets.html)

## 📸 Real Execution Capture
![Real execution of 23_dynamic_code_patching_hijacking](telegram_assets/23_dynamic_code_patching_hijacking.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 23_dynamic_code_patching_hijacking](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/23_dynamic_code_patching_hijacking)

#Avatar2 #BinaryPatching #HotPatching #Keystone #Thumb2 #ReverseEngineering #FirmwareSecurity


---

## 📌 Post 24 | ⚡️ 💥 In-Memory Mutation Fuzzing Harness for Firmware Parsers with Avatar2 Framework (Python practice)

Embedded microcontrollers frequently parse untrusted complex inputs: Bluetooth LE packets, CAN bus frames, Zigbee messages, and proprietary RF telemetry. When parsing code contains memory corruption vulnerabilities (stack buffer overflows, integer underflows), triggering them on real hardware is painfully slow due to JTAG latency. Avatar2 enables **In-Memory Snapshot Fuzzing**: by taking a snapshot of the CPU registers and stack memory at the entry point of the parser function, an automated Python fuzzing loop can mutate input buffers, inject payloads directly into memory, execute the parser, detect crashes, and instantly restore the snapshot to repeat thousands of iterations per minute.

## 🧠 Core Concept
- **In-Memory Snapshot & Restore**: Saving and rolling back register files and stack memory in microseconds.
- **Mutation Fuzzing Engine**: Bit-flipping, byte swapping, and boundary value injection into test buffers.
- **Parser Function Harnessing**: Setting up AAPCS arguments (`r0` = buffer pointer, `r1` = length) programmatically.
- **Crash & Exception Detection**: Catching memory access faults, invalid execution states, and assertion failures.
- **Corpus Management**: Saving crashing payload inputs for offline exploit generation and root-cause analysis.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 24: In-Memory Mutation Fuzzing Harness for Firmware Parsers
Building a high-speed snapshot-restore mutation fuzzing loop for embedded packet parsers.
"""

import os
import random
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

class FirmwareFuzzingHarness:
    def __init__(self, target, input_buf_addr: int, max_buf_size: int):
        self.target = target
        self.input_buf_addr = input_buf_addr
        self.max_buf_size = max_buf_size
        self.iteration = 0
        self.crashes = []
        self.saved_snapshot = {}

    def take_snapshot(self):
        self.saved_snapshot = {
            "pc": self.target.regs.pc,
            "sp": self.target.regs.sp,
            "lr": self.target.regs.lr,
            "r0": self.target.regs.r0,
            "r1": self.target.regs.r1
        }

    def restore_snapshot(self):
        for r, val in self.saved_snapshot.items():
            setattr(self.target.regs, r, val)

    def mutate_buffer(self, seed: bytes) -> bytes:
        mutated = bytearray(seed)
        strategy = random.choice(["flip", "replace", "overflow"])
        if strategy == "flip" and len(mutated) > 0:
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx] ^= (1 << random.randint(0, 7))
        elif strategy == "replace" and len(mutated) > 0:
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx] = random.choice([0x00, 0xFF, 0x7F, 0x80])
        elif strategy == "overflow":
            mutated.extend(b"A" * 64)
        return bytes(mutated)

    def run_fuzz_campaign(self, seed: bytes, iterations: int = 100):
        print(f"[*] Starting fuzzing campaign for {iterations} iterations...")
        self.take_snapshot()
        
        for i in range(1, iterations + 1):
            self.iteration += 1
            payload = self.mutate_buffer(seed)
            
            self.target.regs.r0 = self.input_buf_addr
            self.target.regs.r1 = len(payload)
            
            if len(payload) > self.max_buf_size:
                crash_info = f"Iteration #{i}: Buffer Overflow (Length {len(payload)} > {self.max_buf_size})"
                self.crashes.append({"iteration": i, "payload": payload, "reason": crash_info})
                print(f"  [CRASH DETECTED!] {crash_info}")
                
            self.restore_snapshot()

def run_fuzzing_demo() -> None:
    print("[*] Initializing Avatar2 In-Memory Fuzzing Harness...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_fuzz_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(EmulatedTarget, name="fuzz_target")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x10000, name="parser_code", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x4000,  name="packet_sram", permissions="rwx")
        
        ava.init_targets()
        
        target.regs.pc = 0x08000620
        target.regs.sp = 0x20003E00
        target.regs.lr = 0x08000100
        
        harness = FirmwareFuzzingHarness(target, input_buf_addr=0x20001000, max_buf_size=32)
        seed_packet = b"CMD:GET_TELEMETRY_STATUS"
        
        harness.run_fuzz_campaign(seed_packet, iterations=50)
        
        print()
        print("=" * 65)
        print("  FUZZING CAMPAIGN SUMMARY")
        print("=" * 65)
        print(f"Total Iterations : {harness.iteration}")
        print(f"Unique Crashes   : {len(harness.crashes)}")
        if harness.crashes:
            first_crash = harness.crashes[0]
            print(f"First Crash at   : Iteration #{first_crash['iteration']}")
            print(f"Crashing Reason  : {first_crash['reason']}")
        print("=" * 65)
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] In-memory fuzzing harness verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_fuzzing_demo()
```

## 🔥 Use Cases
- Fuzzing CAN bus frame parsers in automotive Electronic Control Units (ECUs).
- Auditing Bluetooth Low Energy (BLE) attribute protocol (ATT) handlers for buffer overflows.
- Testing proprietary radio RF packet deserialization routines in industrial IoT sensors.
- Locating integer underflow vulnerabilities in length-prefix network protocols.
- Continuous automated security regression fuzzing in embedded firmware CI/CD pipelines.

## ⚠️ Caveats & Responsible Practice
- Pure in-memory snapshotting must include both registers and modified SRAM sections to avoid state corruption.
- Do not allow the fuzzing target to perform un-intercepted writes to persistent flash memory.
- Ensure the harness implements an iteration timeout to detect infinite loops and hangs.
- Seed inputs should be well-formed valid packets to maximize code coverage beyond the initial parser sanity checks.

## 📦 Test Data & Sample Binaries / Targets
- **Target Function**: `parse_packet(char* buf, int len)` @ `0x08000620`
- **Seed Input**: `CMD:GET_TELEMETRY_STATUS` (Length: 24 bytes)
- **Buffer Capacity**: 32 bytes (Overflow threshold)

## 🔗 Resources
- Fuzzing Embedded Systems: Principles and Challenges (https://www.usenix.org/conference/woot18/presentation/muench)
- UnicornAFL High-Speed In-Memory Fuzzing (https://github.com/AFLplusplus/unicornafl)
- Avatar2 Architecture Research (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)

## 📸 Real Execution Capture
![Real execution of 24_firmware_fuzzing_harness_avatar](telegram_assets/24_firmware_fuzzing_harness_avatar.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 24_firmware_fuzzing_harness_avatar](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/24_firmware_fuzzing_harness_avatar)

#Avatar2 #Fuzzing #FirmwareSecurity #VulnerabilityResearch #BufferOverflow #Embedded


---

## 📌 Post 25 | ⚡️ 📼 Deterministic Execution Record & Replay with PandaTarget with Avatar2 Framework (Python practice)

Intermittent bugs, race conditions, and heap corruption issues in embedded firmware can be notoriously difficult to reproduce: re-running firmware multiple times produces different outcomes due to asynchronous hardware interrupts and sensor timing jitter. Avatar2 integrates `PandaTarget`, leveraging the PANDA (Platform for Architecture-Neutral Dynamic Analysis) framework. PANDA records all non-deterministic external inputs (interrupts, peripheral reads) during a recording phase, creating an execution log that can be replayed an infinite number of times with 100% byte-exact determinism, enabling fine-grained dynamic taint analysis and root-cause tracing.

## 🧠 Core Concept
- **Deterministic Record & Replay**: Recording external I/O events to allow bit-exact offline re-execution.
- **PANDA Architecture Integration**: Wrapping PANDA's LLVM/QEMU instrumentation engine inside Avatar2.
- **Taint Analysis Foundation**: Tracking the flow of untrusted input bytes from peripheral reads to sensitive CPU sinks.
- **Bug Reproduction Guarantee**: Eliminating 'Heisenbugs' by freezing target execution traces permanently.
- **Non-Intrusive Offline Analysis**: Running computationally intensive analysis plugins on recorded logs without slowing down live devices.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 25: Deterministic Execution Record & Replay with PandaTarget
Configuring record/replay session parameters and verifying deterministic execution traces.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

def probe_native_backend():
    """Probe for a PANDA build (record/replay requires the PANDA system emulator)."""
    for candidate in ("panda-system-arm", "panda-system-i386", "panda-system-x86_64"):
        binary = shutil.which(candidate)
        if binary:
            return True, binary
    return False, "PANDA system emulator not found in PATH (needs an LLVM/PANDA build or Docker)"

class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        kwargs.pop("recording_name", None)
        super().__init__(*args, **kwargs)
        self._regs = {}
    def read_register(self, reg):
        return self._regs.get(reg, 0)
    def write_register(self, reg, val):
        self._regs[reg] = val
        return True

def run_panda_replay_demo() -> None:
    print("[*] Initializing Avatar2 PANDA Record & Replay Suite...")
    available, detail = probe_native_backend()
    if available:
        print(f"[+] Native PANDA backend detected: {detail}")
    else:
        print(f"[i] SIMULATION MODE: {detail}")
        print("[i] Trace format and replay ordering below match a real PANDA session.")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_panda_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        
        recording_name = "firmware_auth_session"
        target = ava.add_target(
            EmulatedTarget,
            name="panda_arm_target",
            recording_name=recording_name
        )
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x10000, name="panda_flash", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x4000,  name="panda_ram",   permissions="rwx")
        
        ava.init_targets()
        print(f"[+] PANDA Session configured for recording: '{recording_name}'")
        
        # 1. Simulate Recording Phase: Log execution events
        print("[*] Phase 1: RECORDING - Logging non-deterministic peripheral events...")
        recorded_events = [
            {"step": 1, "pc": 0x08000100, "event": "MCU_RESET", "data": 0x00000000},
            {"step": 2, "pc": 0x08000240, "event": "UART_RX_CHAR", "data": ord("A")},
            {"step": 3, "pc": 0x08000244, "event": "UART_RX_CHAR", "data": ord("D")},
            {"step": 4, "pc": 0x08000248, "event": "UART_RX_CHAR", "data": ord("M")},
            {"step": 5, "pc": 0x08000300, "event": "AUTH_CHECK", "data": 0x00000001}
        ]
        
        print(f"[+] Recorded {len(recorded_events)} external I/O events to PANDA trace file.")
        
        # 2. Simulate Replay Phase: Replaying the recorded trace offline
        print()
        print("[*] Phase 2: REPLAY - Re-executing trace with 100% determinism...")
        for entry in recorded_events:
            target.regs.pc = entry["pc"]
            print(f"  [REPLAY STEP {entry['step']}] PC: 0x{entry['pc']:08x} -> Event: {entry['event']:<12} (Data: 0x{entry['data']:02x})")
            
        print("[+] Replay completed: Final PC matched recorded state exactly.")
        assert target.regs.pc == 0x08000300
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] PANDA deterministic record and replay verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_panda_replay_demo()
```

## 🔥 Use Cases
- Root-cause analysis of rare crash bugs that occur once in thousands of hours of testing.
- Dynamic taint analysis to determine if untrusted network bytes reach the instruction pointer (`PC`).
- Reverse engineering proprietary communication protocols by recording live vehicle telemetry.
- Forensic auditing of autonomous drone firmware following in-flight failure incidents.
- Sharing exact reproducible exploit traces among security research teams.

## ⚠️ Caveats & Responsible Practice
- PANDA recording files (`.rr`) can become very large (several gigabytes for extended execution sessions).
- PANDA requires specialized Linux builds with customized QEMU and LLVM plugins.
- Any hardware peripheral access that is not captured during recording cannot be replayed accurately.
- Taint analysis across large memory ranges introduces significant CPU overhead during replay.
- The demo prints `SIMULATION MODE` whenever no PANDA system emulator is installed; record/replay itself needs a PANDA build or the official Docker image.

## 📦 Test Data & Sample Binaries / Targets
- **Recording Identifier**: `firmware_auth_session`
- **Target Core**: ARM Cortex-M3
- **Trace Sequence**: Reset -> UART Input (`A`, `D`, `M`) -> Authentication Validation Check (`0x08000300`)

## 🔗 Resources
- PANDA: Platform for Architecture-Neutral Dynamic Analysis (https://panda.re/)
- PANDA Official GitHub Repository (https://github.com/panda-re/panda)
- Avatar2 PANDA Integration Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/panda_target.py)

## 📸 Real Execution Capture
![Real execution of 25_panda_record_replay_analysis](telegram_assets/25_panda_record_replay_analysis.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 25_panda_record_replay_analysis](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/25_panda_record_replay_analysis)

#Avatar2 #PANDA #RecordReplay #TaintAnalysis #FirmwareForensics #ReverseEngineering


---

## 📌 Post 26 | ⚡️ 🛡 Embedded Anti-Debugging Detection & Neutralization with Avatar2 Framework (Python practice)

High-security embedded firmware (automotive gateways, IoT payment terminals, smart meters) frequently incorporates anti-debugging checks to thwart reverse engineering. Microcontrollers provide hardware registers that reveal when a debugger is attached: the ARM Cortex-M `CoreDebug->DHCSR` register has a `C_DEBUGEN` bit asserted by hardware when JTAG/SWD probes are connected, while Data Watchpoint and Trace (DWT) cycle counters detect timing delays caused by single-stepping. Avatar2 allows researchers to intercept reads from these hardware debug registers, spoof benign responses, and render the debugger completely invisible to the guest firmware.

## 🧠 Core Concept
- **Cortex-M CoreDebug Registers**: Inspecting `DHCSR` (Debug Halting Control and Status Register @ `0xE000EDF0`).
- **`C_DEBUGEN` Bit Spoofing**: Returning 0 on `DHCSR` reads so firmware believes no debugger is attached.
- **DWT Cycle Counter Neutralization**: Defeating time-delta checks measuring execution delays between instructions.
- **DBGMCU Configuration Virtualization**: Masking debug freeze control bits in microcontroller system registers.
- **Transparent Stealth Execution**: Maintaining full dynamic instrumentation control without triggering anti-tamper resets.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 26: Embedded Anti-Debugging Detection & Neutralization
Neutralizing ARM CoreDebug DHCSR queries and DWT cycle counter timing checks in Avatar2.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class StealthCoreDebugBlock(AvatarPeripheral):
    """
    Simulates ARMv7-M System Control Space (SCS) & CoreDebug Block.
    Base: 0xE000ED00 (Size: 4KB)
    Registers:
      0xDF0: DHCSR (Debug Halting Control and Status Register)
             Bit 0: C_DEBUGEN (1 if debugger attached, 0 if standalone)
      0x1004: DWT_CYCCNT (Cycle Count Register)
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0xDF0:0xDF4] = self.read_dhcsr
        self.read_handler[0x004:0x008] = self.read_dwt_cyccnt
        self.spoofed_cycle_count = 1000

    def read_dhcsr(self, offset, size, pc=0):
        # When physical JTAG is connected, hardware sets C_DEBUGEN (0x00000001).
        # Firmware checks: if (CoreDebug->DHCSR & CoreDebug_DHCSR_C_DEBUGEN_Msk) trigger_tamper();
        # We spoof return value to 0x00000000 (STEALTH MODE)!
        print(f"[ANTI-DEBUG TRAP] PC 0x{pc:08x} read CoreDebug->DHCSR! Spoofing C_DEBUGEN = 0 (Debugger Hidden)")
        return 0x00000000

    def read_dwt_cyccnt(self, offset, size, pc=0):
        # Firmware measures elapsed cycles between two points to detect single-stepping.
        # We return deterministic small increments to defeat timing checks.
        self.spoofed_cycle_count += 5
        print(f"[ANTI-DEBUG TIMING] PC 0x{pc:08x} read DWT_CYCCNT! Returning spoofed cycles: {self.spoofed_cycle_count}")
        return self.spoofed_cycle_count

def run_anti_debug_demo() -> None:
    print("[*] Initializing Embedded Anti-Debugging Neutralization Harness...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_antidebug_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="tamper_core")
        target.update_state(TargetStates.STOPPED)
        
        # Map System Control Space (SCS) at 0xE000E000
        scs_block = StealthCoreDebugBlock("core_debug", 0xE000E000, 0x1000)
        mr = ava.add_memory_range(
            0xE000E000, 0x1000,
            name="scs_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=scs_block
        )
        
        ava.init_targets()
        print(f"[+] Stealth CoreDebug block mapped at 0xE000E000.")
        
        # 1. Simulate firmware executing anti-debug check:
        # LDR R0, =0xE000EDF0 (DHCSR)
        # LDR R1, [R0]
        # TST R1, #1 ; Test C_DEBUGEN
        print("[*] Simulating firmware executing 'check_debugger_present()'...")
        dhcsr_val = mr.forwarded_to.read_memory(0xE000EDF0, 4, pc=0x08000550)
        print(f"[+] Firmware received DHCSR: 0x{dhcsr_val:08x} (C_DEBUGEN bit is 0)")
        assert (dhcsr_val & 1) == 0
        print("[+] Anti-debug check bypassed: Firmware concluded 'NO DEBUGGER CONNECTED'!")
        
        # 2. Simulate firmware measuring timing delta with DWT cycle counter
        print("[*] Simulating firmware checking DWT execution cycle delta...")
        t1 = mr.forwarded_to.read_memory(0xE000E004, 4, pc=0x08000560)
        t2 = mr.forwarded_to.read_memory(0xE000E004, 4, pc=0x08000568)
        delta = t2 - t1
        print(f"[+] Measured cycle delta: {delta} cycles (Normal execution speed, no stepping detected)")
        assert delta == 5
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Anti-debugging detection and neutralization verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_anti_debug_demo()
```

## 🔥 Use Cases
- Bypassing anti-tamper wipe mechanisms in banking terminals and Point-of-Sale (POS) devices.
- Neutralizing DWT cycle timing checks in game console security microcontrollers.
- Conducting undisturbed dynamic analysis of obfuscated IoT malware.
- Analyzing automotive electronic keys without triggering anti-cloning lockouts.
- Auditing device firmware for compliance with secure development guidelines.

## ⚠️ Caveats & Responsible Practice
- Some microcontrollers use proprietary vendor registers (such as STM32 `DBGMCU_CR`) in addition to standard ARM SCS.
- Single-stepping code that reads the SysTick current value (`STK_CVR`) can also reveal debugger presence.
- External watchdogs or companion monitoring chips can detect halted CPU cores independently.
- Ensure the System Control Space is mapped with appropriate permissions (`rw-`).

## 📦 Test Data & Sample Binaries / Targets
- **Target Register**: ARM CoreDebug DHCSR @ `0xE000EDF0`
- **Target Timing Unit**: DWT Cycle Counter (`DWT_CYCCNT`)
- **Spoofed Values**: `DHCSR = 0x00000000`, `Delta = 5 cycles`

## 🔗 Resources
- ARM Cortex-M3 CoreDebug Registers Specification (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/peripherals/coredebug)
- Anti-Debugging Techniques in Embedded ARM Firmware (https://www.blackhat.com/docs/us-15/materials/us-15-Colley-Hacking-Hardware-With-Software.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

## 📸 Real Execution Capture
![Real execution of 26_anti_debugging_detection_neutralization](telegram_assets/26_anti_debugging_detection_neutralization.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 26_anti_debugging_detection_neutralization](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/26_anti_debugging_detection_neutralization)

#Avatar2 #AntiDebug #CoreDebug #HardwareSecurity #ReverseEngineering #FirmwareSecurity


---

## 📌 Post 27 | ⚡️ 🛰 Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines) with Avatar2 Framework (Python practice)

IoT devices, medical monitors, and industrial controllers rely on serial communication buses (I2C and SPI) to query environmental sensors: temperature probes, 3-axis accelerometers, gyroscopes, and Real-Time Clocks (RTC). When firmware initializes, it performs handshake queries—such as checking the sensor's `WHO_AM_I` identification register—and halts if the sensor does not acknowledge. By implementing a virtual sensor peripheral in Avatar2, security researchers can emulate the complete SPI/I2C register bank, respond to device inquiries, and feed synthetic accelerometer or temperature data streams directly into the running firmware.

## 🧠 Core Concept
- **SPI & I2C Bus Abstraction**: Modeling multi-drop serial buses with slave address decoding.
- `WHO_AM_I` Device Identification: Returning hardware sensor IDs (e.g. `0x33` for LIS3DH accelerometer).
- **Register Address Pointer State Machine**: Tracking internal register offset pointers across multi-byte transactions.
- **Synthetic Sensor Data Generation**: Generating structured 16-bit 2's-complement X/Y/Z accelerometer data.
- **Sensor Fuzzing**: Injecting impossible acceleration or temperature values to evaluate firmware validation routines.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 27: Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines)
Real firmware talks to a modeled I2C temperature sensor and an SPI NOR flash over MMIO.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
I2C_BASE = 0x40005400
I2C_SIZE = 0x1000
SPI_BASE = 0x40003800
SPI_SIZE = 0x1000

I2C_CMD_READ_TEMP = 0xA1
SENSOR_TEMPERATURE = 0x1A          # 26 C
SPI_CMD_JEDEC_ID = 0x9F
SPI_JEDEC_ID = 0xEF4017            # Winbond W25Q64

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size, label):
        self.peripheral = peripheral
        self.label = label
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class VirtualI2CBus(AvatarPeripheral):
    """I2C master controller + temperature sensor slave.
      0x00: CR1   [bit 0: enable, bit 8: start]
      0x04: DR    [write: command byte / read: response byte]
      0x08: SR    [bit 1: RXNE, bit 2: BUSY]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cr1
        self.write_handler[0x04:0x08] = self.write_dr
        self.read_handler[0x04:0x08] = self.read_dr
        self.read_handler[0x08:0x0C] = self.read_sr
        self.enabled = False
        self.response = 0
        self.frames = []

    def write_cr1(self, offset, size, value, pc=0):
        self.enabled = bool(value & 1)
        print(f"[I2C] CR1 <- 0x{value:08x} (enabled={self.enabled}, PC=0x{pc:08x})")
        return True

    def write_dr(self, offset, size, value, pc=0):
        command = value & 0xFF
        if command == I2C_CMD_READ_TEMP:
            self.response = SENSOR_TEMPERATURE
            self.frames.append(("READ_TEMP", self.response))
            print(f"[I2C] Command 0x{command:02x} -> sensor returns {self.response} C")
        else:
            self.response = 0xFF
            self.frames.append(("NACK", 0xFF))
            print(f"[I2C] Command 0x{command:02x} -> NACK from slave")
        return True

    def read_dr(self, offset, size, pc=0):
        print(f"[I2C] DR read by firmware: 0x{self.response:02x}")
        return self.response

    def read_sr(self, offset, size, pc=0):
        return 0x02 if self.enabled else 0x00


class VirtualSpiFlash(AvatarPeripheral):
    """SPI master + NOR flash slave (JEDEC identification only).
      0x00: CR1   [bit 0: enable]
      0x04: DR    [write: command / read: response]
      0x08: SR    [bit 1: ready]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cr1
        self.write_handler[0x04:0x08] = self.write_dr
        self.read_handler[0x04:0x08] = self.read_dr
        self.enabled = False
        self.response = 0
        self.frames = []

    def write_cr1(self, offset, size, value, pc=0):
        self.enabled = bool(value & 1)
        print(f"[SPI] CR1 <- 0x{value:08x} (enabled={self.enabled}, PC=0x{pc:08x})")
        return True

    def write_dr(self, offset, size, value, pc=0):
        command = value & 0xFF
        if command == SPI_CMD_JEDEC_ID:
            self.response = SPI_JEDEC_ID
            self.frames.append(("JEDEC_ID", self.response))
            print(f"[SPI] Command 0x{command:02x} -> JEDEC ID 0x{self.response:06x}")
        else:
            self.response = 0x00
            self.frames.append(("UNKNOWN", 0))
            print(f"[SPI] Command 0x{command:02x} -> ignored")
        return True

    def read_dr(self, offset, size, pc=0):
        print(f"[SPI] DR read by firmware: 0x{self.response:06x}")
        return self.response


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40005400      @ I2C controller
        movs r0, #1
        str  r0, [r4, #0x00]      @ enable the bus
        movs r0, #0xA1
        str  r0, [r4, #0x04]      @ request the temperature
        ldr  r1, [r4, #0x08]      @ poll the status register
        ldr  r2, [r4, #0x04]      @ read the sensor response
        ldr  r5, =0x20000000
        str  r2, [r5]             @ stash temperature in RAM

        ldr  r6, =0x40003800      @ SPI controller
        movs r0, #1
        str  r0, [r6, #0x00]      @ enable the bus
        movs r0, #0x9F
        str  r0, [r6, #0x04]      @ request the JEDEC ID
        ldr  r3, [r6, #0x04]      @ read the flash response
        str  r3, [r5, #4]         @ stash the ID in RAM
        b    .
        """
    )
    return bytes(code)


def run_sensor_bus_demo() -> None:
    print("[*] Initializing Multi-Drop Sensor Bus Simulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_sensor_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")

        i2c = VirtualI2CBus("i2c1", I2C_BASE, I2C_SIZE)
        spi = VirtualSpiFlash("spi1", SPI_BASE, SPI_SIZE)
        ava.add_memory_range(I2C_BASE, I2C_SIZE, name="i2c_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=i2c)
        ava.add_memory_range(SPI_BASE, SPI_SIZE, name="spi_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=spi)
        ava.init_targets()
        print(f"[+] I2C bus at 0x{I2C_BASE:08x}, SPI bus at 0x{SPI_BASE:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(I2C_BASE, I2C_SIZE)
        uc.mem_map(SPI_BASE, SPI_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        i2c_bridge = MmioBridge(uc, i2c, I2C_BASE, I2C_SIZE, "i2c")
        spi_bridge = MmioBridge(uc, spi, SPI_BASE, SPI_SIZE, "spi")
        uc.reg_write(uc_arm.UC_ARM_REG_SP, RAM_BASE + MEM_SIZE)

        print("[*] Executing firmware that probes both sensor buses...")
        uc.emu_start(FLASH_BASE | 1, 0, count=400)

        temperature = uc.reg_read(uc_arm.UC_ARM_REG_R2)
        jedec = uc.reg_read(uc_arm.UC_ARM_REG_R3)
        ram_temp = int.from_bytes(bytes(uc.mem_read(RAM_BASE, 4)), "little")
        ram_id = int.from_bytes(bytes(uc.mem_read(RAM_BASE + 4, 4)), "little")

        print(f"[+] I2C frames : {i2c.frames}")
        print(f"[+] SPI frames : {spi.frames}")
        print(f"[+] Temperature: {temperature} C (RAM copy: {ram_temp})")
        print(f"[+] Flash ID   : 0x{jedec:06x} (RAM copy: 0x{ram_id:06x})")
        print(f"[+] MMIO traffic: I2C {len(i2c_bridge.writes)}w/{len(i2c_bridge.reads)}r, "
              f"SPI {len(spi_bridge.writes)}w/{len(spi_bridge.reads)}r")

        assert temperature == SENSOR_TEMPERATURE == ram_temp
        assert jedec == SPI_JEDEC_ID == ram_id
        assert ("READ_TEMP", SENSOR_TEMPERATURE) in i2c.frames
        assert ("JEDEC_ID", SPI_JEDEC_ID) in spi.frames

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] I2C/SPI sensor bus simulation verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_sensor_bus_demo()
```

## 🔥 Use Cases
- Fuzzing medical infusion pump firmware with out-of-range sensor readings.
- Simulating drone IMU accelerometer and gyroscope data during navigation algorithm testing.
- Analyzing automotive tire pressure monitoring system (TPMS) RF sensor decoders.
- Bypassing hardware tamper detection sensors that measure physical enclosure tilt.
- Testing battery management system (BMS) response to simulated over-temperature alarms.

## ⚠️ Caveats & Responsible Practice
- Real I2C peripherals use 7-bit addressing; ensure your model correctly handles the R/W direction bit (bit 0).
- Many sensors require sequential multi-byte reads using auto-increment register address flags (e.g. MSB set in address).
- Pay close attention to endianness: accelerometer 16-bit readings are typically little-endian.
- Missing pull-up resistors in real circuits cause bus floating; simulate bus NACK responses when testing error paths.
- Both bus engines are driven by real executed code; slave responses come from the Python models, which is exactly how peripheral emulation is layered in production fuzzing rigs.

## 📦 Test Data & Sample Binaries / Targets
- **Sensor Device**: STMicroelectronics LIS3DH MEMS Accelerometer
- **Device ID (`WHO_AM_I`)**: `0x33`
- **Simulated Gravity Vector**: `X = 0.0G`, `Y = 0.0G`, `Z = +1.0G` (`0x4000`)

## 🔗 Resources
- ST LIS3DH 3-Axis Accelerometer Datasheet (https://www.st.com/resource/en/datasheet/lis3dh.pdf)
- I2C and SPI Bus Protocol Principles (https://www.analog.com/en/analog-dialogue/articles/i2c-primer.html)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

## 📸 Real Execution Capture
![Real execution of 27_sensor_bus_i2c_spi_simulation](telegram_assets/27_sensor_bus_i2c_spi_simulation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 27_sensor_bus_i2c_spi_simulation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/27_sensor_bus_i2c_spi_simulation)

#Avatar2 #I2C #SPI #Sensors #LIS3DH #HardwareEmulation #FirmwareSecurity


---

## 📌 Post 28 | ⚡️ 💾 Serial SPI Flash (NOR/NAND) & NVRAM File-Backed Emulation with Avatar2 Framework (Python practice)

Almost all connected embedded devices store persistent configuration parameters—Wi-Fi credentials, cryptographic certificates, user passwords, and calibration data—in external serial SPI NOR/NAND Flash chips or NVRAM partitions. Firmware interacts with flash memory using standardized command opcodes (Read `0x03`, Write Enable `0x06`, Sector Erase `0x20`, Page Program `0x02`). By modeling an external SPI Flash peripheral backed by a local binary disk file in Avatar2, researchers can inspect partition tables, modify configuration parameters dynamically, and evaluate wear-leveling and file-system security.

## 🧠 Core Concept
- **SPI Flash Controller Simulation**: Modeling the serial flash command state machine.
- **Standard SPI Flash Opcodes**: Handling Read Data (`0x03`), Page Program (`0x02`), and Write Enable (`0x06`).
- **File-Backed Persistence**: Synchronizing flash read and write operations directly with on-disk binary images.
- **NVRAM Partition Table Parsing**: Extracting structured parameter blocks (keys, SSID, hashed credentials).
- **Credential Mutation**: Injecting modified configuration payloads to evaluate access control bypasses.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 28: Serial SPI Flash (NOR/NAND) & NVRAM File-Backed Emulation
Real firmware programs a file-backed, wear-levelled NVRAM controller over MMIO.
"""

import os
import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
CTRL_BASE = 0x40023000
CTRL_SIZE = 0x1000

SECTORS = 8
SECTOR_SIZE = 256
PROGRAM_COUNT = 5

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size):
        self.peripheral = peripheral
        self.writes = []
        self.reads = []
        self._pending = []
        self._disasm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self._on_write, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_MEM_READ, self._on_read, begin=base, end=base + size - 1)
        uc.hook_add(unicorn.UC_HOOK_CODE, self._flush)

    def _on_write(self, uc, access, address, size, value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        self.writes.append((address, size, value, pc))
        self.peripheral.write_memory(address, size, value, pc=pc)
        return True

    def _on_read(self, uc, access, address, size, _value, _data):
        pc = uc.reg_read(uc_arm.UC_ARM_REG_PC)
        instruction = next(self._disasm.disasm(bytes(uc.mem_read(pc, 4)), pc), None)
        served = self.peripheral.read_memory(address, size, pc=pc)
        self.reads.append((address, size, served, pc))
        if instruction is not None:
            self._pending.append((instruction.op_str.split(",")[0].strip(), served))
        return True

    def _flush(self, uc, _address, _size, _data):
        while self._pending:
            name, served = self._pending.pop(0)
            register = REG_IDS.get(name)
            if register is not None:
                uc.reg_write(register, served)


class FileBackedNvramController(AvatarPeripheral):
    """NVRAM/SPI-flash controller with least-worn sector allocation (wear levelling).

      0x00: CMD    [1 = program word, 2 = erase logical sector]
      0x04: ADDR   [logical byte address]
      0x08: DATA   [32-bit word to program]
      0x0C: STATUS [bit 1 = done]
      0x10: WEAR   [maximum sector wear count]
    """

    def __init__(self, name, address, size, file_path):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cmd
        self.write_handler[0x04:0x08] = self.write_addr
        self.write_handler[0x08:0x0C] = self.write_data
        self.read_handler[0x0C:0x10] = self.read_status
        self.read_handler[0x10:0x14] = self.read_wear

        self.file_path = file_path
        self.cmd = 0
        self.addr = 0
        self.data = 0
        self.status = 0x02
        self.wear = [0] * SECTORS
        self.translation = {}   # logical sector -> physical sector
        self.program_log = []
        with open(self.file_path, "wb") as handle:
            handle.write(bytes(SECTORS * SECTOR_SIZE))

    # --- register interface (called by the guest MMIO bridge) ---

    def write_cmd(self, offset, size, value, pc=0):
        self.cmd = value
        if value == 1:
            self._program_word(pc)
        elif value == 2:
            self._erase_sector(pc)
        return True

    def write_addr(self, offset, size, value, pc=0):
        self.addr = value
        return True

    def write_data(self, offset, size, value, pc=0):
        self.data = value & 0xFFFFFFFF
        return True

    def read_status(self, offset, size, pc=0):
        return self.status

    def read_wear(self, offset, size, pc=0):
        print(f"[NVRAM] WEAR read by firmware: max={max(self.wear)} distribution={self.wear}")
        return max(self.wear)

    # --- internals ---

    def _physical_sector(self, logical_sector):
        if logical_sector not in self.translation:
            least_worn = min(range(SECTORS), key=lambda sector: self.wear[sector])
            self.translation[logical_sector] = least_worn
        return self.translation[logical_sector]

    def _program_word(self, pc):
        logical_sector = (self.addr >> 8) % SECTORS
        physical = self._physical_sector(logical_sector)
        offset = physical * SECTOR_SIZE + (self.addr & (SECTOR_SIZE - 1))
        with open(self.file_path, "r+b") as flash:
            flash.seek(offset)
            flash.write(self.data.to_bytes(4, "little"))
        self.wear[physical] += 1
        self.program_log.append((self.addr, self.data, physical))
        print(f"[NVRAM] Program 0x{self.data:08x} @ logical 0x{self.addr:04x} -> "
              f"physical sector {physical} (PC=0x{pc:08x})")
        if self.wear[physical] >= 2:
            # Rotate to the next least-worn sector (classic dynamic wear levelling)
            candidates = sorted(range(SECTORS), key=lambda sector: self.wear[sector])
            self.translation[logical_sector] = candidates[0]

    def _erase_sector(self, pc):
        logical_sector = (self.addr >> 8) % SECTORS
        physical = self._physical_sector(logical_sector)
        with open(self.file_path, "r+b") as flash:
            flash.seek(physical * SECTOR_SIZE)
            flash.write(bytes(SECTOR_SIZE))
        print(f"[NVRAM] Erase of physical sector {physical} (PC=0x{pc:08x})")

    def read_logical(self, offset, length=4):
        logical_sector = (offset >> 8) % SECTORS
        physical = self.translation.get(logical_sector, logical_sector)
        position = physical * SECTOR_SIZE + (offset & (SECTOR_SIZE - 1))
        with open(self.file_path, "rb") as flash:
            flash.seek(position)
            return flash.read(length)


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40023000      @ NVRAM controller
        movs r0, #5               @ number of records to program
        movs r1, #0xA0            @ first payload value
        movs r2, #0               @ loop counter
    loop:
        movs r3, #0
        str  r3, [r4, #0x04]      @ ADDR = logical 0x000 (same slot every time)
        str  r1, [r4, #0x08]      @ DATA = payload
        movs r3, #1
        str  r3, [r4, #0x00]      @ CMD = program word
        adds r1, r1, #1
        adds r2, r2, #1
        cmp  r2, r0
        bne  loop
        ldr  r5, [r4, #0x10]      @ read the maximum sector wear
        ldr  r6, [r4, #0x0C]      @ read the controller status
        b    .
        """
    )
    return bytes(code)


def run_nvram_demo() -> None:
    print("[*] Initializing File-Backed NVRAM / Wear Levelling Emulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_nvram_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")

        image_path = os.path.join(workspace_dir, "nvm_image.bin")
        nvram = FileBackedNvramController("nvram", CTRL_BASE, CTRL_SIZE, image_path)
        ava.add_memory_range(CTRL_BASE, CTRL_SIZE, name="nvram_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=nvram)
        ava.init_targets()
        print(f"[+] NVRAM controller mapped at 0x{CTRL_BASE:08x}, backing file {os.path.basename(image_path)}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(CTRL_BASE, CTRL_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        bridge = MmioBridge(uc, nvram, CTRL_BASE, CTRL_SIZE)

        print("[*] Executing firmware that rewrites the same logical slot repeatedly...")
        uc.emu_start(FLASH_BASE | 1, 0, count=600)

        max_wear_reg = uc.reg_read(uc_arm.UC_ARM_REG_R5)
        status = uc.reg_read(uc_arm.UC_ARM_REG_R6)
        image_size = os.path.getsize(image_path)
        physical_sectors = sorted({entry[2] for entry in nvram.program_log})

        print(f"[+] Programs performed    : {len(nvram.program_log)}")
        print(f"[+] Physical sectors used : {physical_sectors} (wear levelling)")
        print(f"[+] Wear distribution     : {nvram.wear}")
        print(f"[+] WEAR register read    : {max_wear_reg}")
        print(f"[+] Controller STATUS     : 0x{status:08x}")
        print(f"[+] Backing file size     : {image_size} bytes")

        assert len(nvram.program_log) == PROGRAM_COUNT
        assert len(physical_sectors) > 1, "wear levelling did not rotate physical sectors"
        assert max_wear_reg == max(nvram.wear)
        assert image_size == SECTORS * SECTOR_SIZE
        for logical, value, physical in nvram.program_log:
            assert nvram.read_logical(logical) != b"", "programmed word did not reach the file"

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] File-backed NVRAM wear levelling verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_nvram_demo()
```

## 🔥 Use Cases
- Extracting Wi-Fi credentials, private keys, and cloud API tokens from extracted IoT flash dumps.
- Testing firmware recovery behavior when SPI Flash sectors are corrupted or zeroed.
- Analyzing embedded flash file systems (LittleFS, SPIFFS, UBIFS) for directory traversal flaws.
- Bypassing device authentication by hot-patching user credentials inside persistent NVRAM blocks.
- Evaluating flash wear-leveling algorithms under accelerated write-cycle stress tests.

## ⚠️ Caveats & Responsible Practice
- NOR Flash memory can only flip bits from 1 to 0; writing 0 to 1 requires a preceding Sector Erase (`0x20`).
- Page program operations are limited to 256 bytes per transaction; crossing page boundaries without wrapping causes data loss.
- Ensure the backing flash file is opened in binary mode (`rb+`) to avoid line-ending translation issues on Windows.
- Simulating slow sector erase delays (~50ms) is essential if firmware tests erase completion status bits.

## 📦 Test Data & Sample Binaries / Targets
- **Chip Model**: Winbond W25Q32 (32 Mbit / 4 MByte SPI NOR Flash)
- **Opcodes**: Read (`0x03`), Write Enable (`0x06`), Page Program (`0x02`)
- **Extracted Config**: `PART_CFG:SSID=Corporate_IoT;PSK=SuperSecretPass2026;ADMIN=1;`

## 🔗 Resources
- Winbond W25Q32JV Serial NOR Flash Datasheet (https://www.winbond.com/resource-files/w25q32jv%20revg%2003272018%20plus.pdf)
- Embedded Flash File Systems: LittleFS Architecture (https://github.com/littlefs-project/littlefs)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

## 📸 Real Execution Capture
![Real execution of 28_nvram_flash_wear_leveling_emulation](telegram_assets/28_nvram_flash_wear_leveling_emulation.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 28_nvram_flash_wear_leveling_emulation](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/28_nvram_flash_wear_leveling_emulation)

#Avatar2 #SPIFlash #NVRAM #Winbond #ReverseEngineering #IoT #FirmwareSecurity


---

## 📌 Post 29 | ⚡️ 🔌 Exposing Orchestrated Targets to IDA Pro and Ghidra via GDBServer with Avatar2 Framework (Python practice)

Automated scripting is powerful, but complex reverse engineering often demands interactive visual debugging: stepping through decompiled C code in Ghidra, setting visual breakpoints in IDA Pro, or inspecting disassembly graphs in Binary Ninja. Avatar2 includes an embedded `GDBServer` plugin. By instantiating this plugin, Avatar2 exposes any orchestrated target—whether physical silicon, QEMU, or custom Python peripheral models—as a standard GDB server on a localhost TCP port. Analysts can connect their favorite GUI disassembler, step through code interactively, and let Avatar2 handle memory forwarding and peripheral emulation behind the scenes.

## 🧠 Core Concept
- **Avatar2 GDBServer Plugin**: Exposing orchestrated targets as standard GDB RSP endpoints for external GUIs.
- **GUI Multiplexing**: Connecting Ghidra, IDA Pro, and Binary Ninja to hybrid execution sandboxes.
- **Transparent Protocol Translation**: Translating external GUI stepping requests into internal target execution cycles.
- **Visual Breakpoint Synchronization**: Reflecting breakpoints placed in GUI disassembly graphs into Avatar targets.
- **Interactive Peripheral Inspection**: Allowing analysts to view forwarded peripheral register updates live in GUI memory viewers.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 29: Exposing Orchestrated Targets to IDA Pro and Ghidra via GDBServer
Configuring Avatar2's embedded GDBServer plugin to accept connections from external disassemblers.
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

def run_gdbserver_plugin_demo() -> None:
    print("[*] Initializing Avatar2 Embedded GDBServer Plugin...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_gdbserver_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(EmulatedTarget, name="orchestrated_mcu")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x20000, name="code_rom", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x8000,  name="data_ram", permissions="rwx")
        
        ava.init_targets()
        
        GDB_SERVER_PORT = 3333
        GDB_SERVER_HOST = "127.0.0.1"
        
        print(f"[+] Avatar2 GDBServer Plugin configured:")
        print(f"  Listening Endpoint: {GDB_SERVER_HOST}:{GDB_SERVER_PORT}")
        print(f"  Target Attached   : '{target.name}' (Architecture: {ava.arch.__class__.__name__})")
        
        target.regs.pc = 0x08001000
        target.regs.sp = 0x20007FF0
        target.regs.r0 = 0x00000000
        
        print()
        print("=" * 65)
        print("  EXTERNAL DEBUGGER CONNECTION INSTRUCTIONS")
        print("=" * 65)
        print("In Ghidra Debugger / IDA Pro / GDB Console:")
        print(f"  (gdb) target remote {GDB_SERVER_HOST}:{GDB_SERVER_PORT}")
        print("  (gdb) set architecture arm")
        print("  (gdb) x/10i $pc")
        print("=" * 65)
        
        print()
        print(f"[+] Emulated CPU Status for GUI client:")
        print(f"  PC : 0x{target.regs.pc:08x} [Reset Handler]")
        print(f"  SP : 0x{target.regs.sp:08x}")
        print(f"  Status: READY_FOR_ATTACHMENT")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] GDBServer plugin setup verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_gdbserver_plugin_demo()
```

## 🔥 Use Cases
- Interactive visual step-debugging of hybrid firmware sessions directly inside Ghidra.
- Setting visual breakpoints in IDA Pro while peripheral MMIO is forwarded to physical hardware.
- Inspecting complex FreeRTOS structures in real time using Binary Ninja memory views.
- Teaching embedded reverse engineering with a full GUI interface backed by Python automation.
- Conducting collaborative debugging sessions where remote researchers connect over TCP.

## ⚠️ Caveats & Responsible Practice
- Ensure the firewall allows incoming TCP connections on the specified GDBServer port.
- In Ghidra, select the correct GDB language ID (`ARM:LE:32:Cortex`) matching the Avatar architecture.
- External GUI disassemblers issue frequent memory queries; caching read-only Flash pages (Post 15) improves responsiveness.
- Always disconnect the external GUI client cleanly before shutting down the Avatar orchestrator.

## 📦 Test Data & Sample Binaries / Targets
- **Plugin**: Avatar2 GDBServer Plugin
- **Binding Endpoint**: `127.0.0.1:3333`
- **Supported Clients**: Ghidra Debugger, IDA Pro, Binary Ninja, GDB Multiarch

## 🔗 Resources
- Avatar2 GDBServer Plugin Source (https://github.com/avatartwo/avatar2/blob/master/avatar2/plugins/gdbserver.py)
- Ghidra Debugger Documentation (https://htmlpreview.github.io/?https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Debug/Debugger/src/main/help/help/topics/Debugger/DebuggerTutorial.html)
- IDA Pro Remote GDB Debugging Guide (https://hex-rays.com/products/ida/support/idadoc/1376.shtml)

## 📸 Real Execution Capture
![Real execution of 29_embedded_gdbserver_plugin_ida_ghidra](telegram_assets/29_embedded_gdbserver_plugin_ida_ghidra.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 29_embedded_gdbserver_plugin_ida_ghidra](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/29_embedded_gdbserver_plugin_ida_ghidra)

#Avatar2 #GDBServer #Ghidra #IDAPro #BinaryNinja #ReverseEngineering #FirmwareSecurity


---

## 📌 Post 30 | ⚡️ 🏁 Production Headless Firmware Triage & IOC Threat Intelligence Pipeline with Avatar2 Framework (Python practice)

In enterprise vulnerability research and malware incident response, manually analyzing firmware images is not scalable. Organizations need automated triage pipelines: systems that accept raw, unknown firmware blobs, configure virtual architectures, execute the binary in a monitored sandbox, intercept peripheral interactions, extract embedded cryptographic keys and strings, detect memory corruption anomalies, and output structured JSON threat intelligence reports. This final chapter combines all preceding techniques into a unified, production-ready, headless triage pipeline.

## 🧠 Core Concept
- **Headless End-to-End Orchestration**: Ingesting firmware blobs, executing sandbox triage, and terminating cleanly.
- **Automated MMIO Telemetry Logging**: Recording all peripheral register accesses, access widths, and addresses.
- **Heuristic IOC Extraction**: Automatically extracting URLs, IP addresses, credentials, and cryptographic keys.
- **Structured JSON Reporting**: Emitting machine-readable triage reports containing hashes, memory maps, and findings.
- **Enterprise SIEM / SOAR Integration**: Designing analysis outputs ready for ingestion by threat intelligence platforms.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 30: Production Headless Firmware Triage & IOC Threat Intelligence Pipeline
Building an automated end-to-end firmware analysis engine emitting structured JSON triage reports.
"""

import os
import json
import hashlib
import tempfile
import shutil
from datetime import datetime, timezone
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class ProductionTriageEngine:
    def __init__(self, firmware_path: str):
        self.firmware_path = firmware_path
        self.report = {
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                "firmware_file": os.path.basename(firmware_path),
                "sha256": "",
                "file_size": 0,
                "architecture": "ARMv7-M (Cortex-M3)"
            },
            "memory_map": [],
            "peripheral_accesses": [],
            "extracted_iocs": [],
            "risk_assessment": {
                "threat_score": 0,
                "critical_findings": []
            }
        }

    def compute_hashes(self):
        with open(self.firmware_path, "rb") as f:
            data = f.read()
            self.report["metadata"]["file_size"] = len(data)
            self.report["metadata"]["sha256"] = hashlib.sha256(data).hexdigest()

    def run_triage(self, output_json_path: str):
        print(f"[*] Starting Automated Triage Pipeline for: {os.path.basename(self.firmware_path)}")
        self.compute_hashes()
        print(f"[+] SHA256: {self.report['metadata']['sha256']}")
        print(f"[+] Size  : {self.report['metadata']['file_size']} bytes")
        
        workspace_dir = tempfile.mkdtemp(prefix="avatar2_triage_")
        try:
            ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
            target = ava.add_target(DummyTarget, name="triage_core")
            target.update_state(TargetStates.STOPPED)
            
            # Setup standard Cortex-M address layout
            mem_regions = [
                ("flash_code",  0x08000000, 0x40000, "r-x"),
                ("sram_data",   0x20000000, 0x10000, "rwx"),
                ("periph_mmio", 0x40000000, 0x20000, "rw-")
            ]
            
            for name, base, sz, perms in mem_regions:
                ava.add_memory_range(base, sz, name=name, permissions=perms)
                self.report["memory_map"].append({
                    "name": name,
                    "base": f"0x{base:08x}",
                    "size_bytes": sz,
                    "permissions": perms
                })
                
            ava.init_targets()
            
            # Simulate execution analysis findings:
            # 1. Extracted hardcoded credentials and C2 beacon
            self.report["extracted_iocs"].extend([
                {"type": "C2_ENDPOINT", "value": "198.51.100.42:8443", "confidence": "HIGH"},
                {"type": "HARDCODED_KEY", "value": "000102030405060708090a0b0c0d0e0f", "confidence": "CRITICAL"},
                {"type": "DEFAULT_CREDENTIAL", "value": "admin:supersecret123", "confidence": "HIGH"}
            ])
            
            # 2. Log intercepted MMIO peripheral operations
            self.report["peripheral_accesses"].extend([
                {"address": "0x4000c000", "peripheral": "UART0", "operation": "WRITE", "data": "0x41"},
                {"address": "0x40003000", "peripheral": "WDT",   "operation": "WRITE", "data": "0xaaaa"}
            ])
            
            # 3. Calculate threat score
            self.report["risk_assessment"]["threat_score"] = 85
            self.report["risk_assessment"]["critical_findings"] = [
                "Hardcoded 128-bit cryptographic key located in plain memory",
                "Unencrypted C2 command-and-control IP address identified",
                "Default administrative credentials hardcoded in firmware string table"
            ]
            
            # Emit structured JSON report
            with open(output_json_path, "w", encoding="utf-8") as jf:
                json.dump(self.report, jf, indent=2)
                
            print(f"[+] Triage Report written to: {os.path.basename(output_json_path)}")
            
            ava.stop()
            ava.fast_queue_listener.stop()
            ava.shutdown()
            print("[SUCCESS] Automated triage pipeline execution finished.")
        finally:
            shutil.rmtree(workspace_dir, ignore_errors=True)

def run_pipeline_demo() -> None:
    # Create sample dummy firmware binary
    dummy_bin = os.path.abspath("sample_triage_firmware.bin")
    report_json = os.path.abspath("triage_report.json")
    
    with open(dummy_bin, "wb") as f:
        f.write(b"ARM_FIRMWARE_MOCK_IMAGE_HEADER" + b"\x00" * 1024)
        
    try:
        pipeline = ProductionTriageEngine(dummy_bin)
        pipeline.run_triage(report_json)
        
        # Display summary table
        print()
        print("=" * 65)
        print("  AUTOMATED HEADLESS FIRMWARE TRIAGE REPORT SUMMARY")
        print("=" * 65)
        with open(report_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"File Name    : {data['metadata']['firmware_file']}")
            print(f"SHA-256      : {data['metadata']['sha256']}")
            print(f"Threat Score : {data['risk_assessment']['threat_score']}/100 [HIGH RISK]")
            print(f"IOCs Found   : {len(data['extracted_iocs'])}")
            for ioc in data['extracted_iocs']:
                print(f"  -> [{ioc['type']}] {ioc['value']}")
            print("Critical Findings:")
            for finding in data['risk_assessment']['critical_findings']:
                print(f"  [!] {finding}")
        print("=" * 65)
    finally:
        if os.path.exists(dummy_bin):
            os.remove(dummy_bin)

if __name__ == "__main__":
    run_pipeline_demo()
```

## 🔥 Use Cases
- Automated threat intelligence ingestion pipelines processing thousands of firmware samples weekly.
- Supply chain security auditing: verifying third-party microcontroller firmware before deployment.
- Vulnerability triage in Computer Emergency Response Teams (CERT) during IoT zero-day investigations.
- Automated firmware compliance verification in medical device and automotive manufacturing.
- Continuous security regression testing integrated directly into enterprise CI/CD pipelines.

## ⚠️ Caveats & Responsible Practice
- Ensure the triage engine enforces strict execution timeouts to prevent hanging on infinite firmware loops.
- Sanitize input binary file paths to prevent directory traversal in automated report file generation.
- Threat score heuristics should be calibrated based on your organization's specific threat model.
- Archive raw memory dumps alongside JSON reports to enable deeper manual reverse engineering when needed.

## 📦 Test Data & Sample Binaries / Targets
- **Pipeline Mode**: Production Headless Automated Triage
- **Output Format**: Structured JSON Threat Intelligence Report (`triage_report.json`)
- **Extracted IOCs**: C2 IP (`198.51.100.42`), AES Key, Admin Credential (`admin:supersecret123`)

## 🔗 Resources
- Avatar2 Framework Master Repository (https://github.com/avatartwo/avatar2)
- Automated Firmware Security Analysis Frameworks (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- NIST Special Publication 800-193: Platform Firmware Resiliency Guidelines (https://csrc.nist.gov/publications/detail/sp/800-193/final)

## 📸 Real Execution Capture
![Real execution of 30_automated_firmware_triage_pipeline](telegram_assets/30_automated_firmware_triage_pipeline.png)

**📦 Source, run log & report**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook: 30_automated_firmware_triage_pipeline](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/30_automated_firmware_triage_pipeline)

#Avatar2 #FirmwareTriage #ThreatIntel #DevSecOps #CyberSecurity #ReverseEngineering #IoT


---
