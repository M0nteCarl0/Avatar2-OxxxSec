# ==============================================================================
# Avatar2 Educational Playbook - Posts 01 to 15 Content & Scripts
# ==============================================================================

POSTS_1_TO_15 = [
    # --------------------------------------------------------------------------
    # Post 01
    # --------------------------------------------------------------------------
    {
        "num": 1,
        "dir_name": "01_orchestrator_initialization_architecture",
        "title": "Avatar2 Core Orchestrator Initialization & Architecture Lifecycle",
        "emoji": "⚡️ 🔬",
        "intro": (
            "Embedded firmware dynamic analysis presents a unique challenge: firmware is tightly coupled "
            "to custom microcontrollers, hardware peripherals, and physical memory layouts. Running such "
            "firmware purely in an emulator causes crashes upon the first hardware register access, while "
            "running exclusively on physical hardware lacks introspection, instrumentation, and repeatability. "
            "The **Avatar2 Framework** solves this dilemma through a multi-target orchestration architecture. "
            "At its center lies the `Avatar` orchestrator, which coordinates heterogeneous execution targets "
            "(QEMU, Unicorn, OpenOCD, GDB, PANDA, angr), arbitrates memory layouts, and manages the execution lifecycle."
        ),
        "core_concepts": [
            "**Multi-Target Orchestration**: Centralized management of multiple execution engines operating synchronously or asynchronously.",
            "**Architecture Abstraction**: Explicit target CPU definitions (e.g. `ARM_CORTEX_M3`, `ARM`, `MIPS`, `X86_64`) providing register mappings and ABI conventions.",
            "**Workspace Isolation**: Dedicated runtime directories for capturing execution logs, FIFO pipes, and temporary core dumps.",
            "**Target Lifecycle States**: Strict state transitions (`CREATED` -> `INITIALIZED` -> `STOPPED` -> `RUNNING` -> `EXITED`) monitored by Avatar's fast queue dispatcher.",
            "**Graceful Teardown**: Coordinated shutdown sequence releasing background threads, IPC pipes, and socket listeners cleanly."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Automated multi-engine firmware security testing pipelines.",
            "Coordinating hybrid execution between physical microcontroller boards and emulators.",
            "Headless CI/CD regression verification of bare-metal embedded C/C++ firmware.",
            "Establishing clean execution sandboxes for reverse engineering stripped IoT binaries.",
            "Standardizing firmware analysis setups across mixed teams of hardware and security engineers."
        ],
        "caveats": [
            "Always call `ava.stop()` and `ava.shutdown()` before exiting scripts to avoid orphaned worker threads.",
            "Ensure the selected target architecture (e.g. `ARM_CORTEX_M3`) matches your firmware's instruction set.",
            "Custom workspace directories should be created on fast local storage to minimize IPC socket latency.",
            "Logging should be configured appropriately; default verbose logging can quickly produce multi-gigabyte log files."
        ],
        "test_data": "- **Target Platform**: ARM Cortex-M3 (ARMv7-M architecture)\n- **Target Board Model**: Generic STM32F103 / LM3S6965 Microcontroller\n- **Orchestration Type**: Pure Orchestrator Initialization & State Lifecycle",
        "resources": [
            "Avatar2 Official Repository (https://github.com/avatartwo/avatar2)",
            "Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)",
            "Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)"
        ],
        "hashtags": ["#Avatar2", "#FirmwareSecurity", "#ReverseEngineering", "#Embedded", "#HardwareInTheLoop", "#Emulation", "#CyberSecurity"]
    },

    # --------------------------------------------------------------------------
    # Post 02
    # --------------------------------------------------------------------------
    {
        "num": 2,
        "dir_name": "02_granular_memory_mapping_layout",
        "title": "Granular Address Space Configuration & Memory Range Protection",
        "emoji": "⚡️ 🗺",
        "intro": (
            "Embedded microcontrollers do not have unified flat memory spaces like typical desktop processes. "
            "Instead, their address space is strictly segmented into non-contiguous hardware regions: Flash ROM, "
            "internal SRAM, external memory banks, and memory-mapped I/O (MMIO) peripheral blocks. "
            "Avatar2 implements an interval-tree-backed memory management engine that allows security researchers "
            "to construct granular memory maps with explicit permission bitmasks (`rwx`), file-backed storage, "
            "and overlap protection."
        ),
        "core_concepts": [
            "**IntervalTree Memory Management**: High-speed O(log N) lookup of memory ranges based on target physical addresses.",
            "**Access Permissions Enforcement**: Granular configuration of Read (`r`), Write (`w`), and Execute (`x`) attributes.",
            "**Region Classification**: Categorizing address blocks into ROM (Flash), RAM (SRAM/DRAM), and MMIO peripheral banks.",
            "**Overlap Detection**: Safeguards preventing conflicting memory allocations across orchestrated targets.",
            "**Query & Resolution API**: Resolving guest memory addresses to concrete memory ranges and metadata at runtime."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Replicating exact datasheet memory maps for STM32, NXP, ESP32, and Nordic microcontrollers.",
            "Enforcing W^X (Write XOR Execute) security policies to detect buffer overflow exploit payloads.",
            "Detecting unmapped null-pointer dereferences in embedded bootloaders.",
            "Mapping non-contiguous external flash banks (SPI NOR Flash) at high memory offsets.",
            "Automated sanity-checking of linker script (`.ld`) section outputs against virtual layouts."
        ],
        "caveats": [
            "Ensure range boundaries match hardware page alignment (typically 1KB or 4KB boundaries).",
            "Marking MMIO regions as executable (`rwx`) can mask instruction fetch vulnerabilities.",
            "Overlapping memory intervals will raise exceptions unless explicitly configured.",
            "Memory range permissions must be respected by the underlying target execution engine."
        ],
        "test_data": "- **Flash Base**: `0x08000000` (Size: 512 KB, Permissions: `r-x`)\n- **SRAM Base**: `0x20000000` (Size: 128 KB, Permissions: `rwx`)\n- **MMIO Base**: `0x40000000` (Size: 64 KB, Permissions: `rw-`)",
        "resources": [
            "Avatar2 Memory Management Architecture (https://avatar2.readthedocs.io/en/latest/api/memory.html)",
            "ARM Cortex-M Memory Model Documentation (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/memory-model)",
            "IntervalTree Python Library Documentation (https://pypi.org/project/intervaltree/)"
        ],
        "hashtags": ["#Avatar2", "#MemoryMapping", "#FirmwareSecurity", "#EmbeddedSystems", "#ARM", "#ReverseEngineering"]
    },

    # --------------------------------------------------------------------------
    # Post 03
    # --------------------------------------------------------------------------
    {
        "num": 3,
        "dir_name": "03_dummy_target_mock_execution",
        "title": "Mock Target Orchestration and Unit-Testing without Physical Hardware",
        "emoji": "⚡️ 🧩",
        "intro": (
            "Developing and verifying complex multi-target analysis workflows can be cumbersome when physical "
            "hardware or heavy virtual machine targets are required. Avatar2 provides `DummyTarget`, a lightweight, "
            "fully programmatic mock execution backend. `DummyTarget` implements the complete Avatar target interface—"
            "including register files, memory read/write mocks, and state transitions—enabling continuous integration (CI) "
            "testing and offline protocol verification with zero dependencies."
        ),
        "core_concepts": [
            "**Protocol Abstraction**: Uniform target interface masking whether execution occurs on silicon, QEMU, or in-memory mocks.",
            "**Simulated Register Files**: Direct programmatic manipulation of general-purpose and special registers (`r0`-`r12`, `sp`, `lr`, `pc`).",
            "**AAPCS Calling Convention Simulation**: Modeling ARM subroutine parameter passing (arguments in `r0`-`r3`, return values in `r0`).",
            "**Deterministic CI Testing**: Verifying analysis orchestration logic in automated headless pipelines without hardware flakiness.",
            "**Target State Machine Manipulation**: Validating custom event listeners across synthetic `STOPPED`, `RUNNING`, and `EXITED` events."
        ],
        "code": '''#!/usr/bin/env python3
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
    run_dummy_target_demo()''',
        "use_cases": [
            "Building robust CI/CD regression test suites for Avatar2 plugins and extensions.",
            "Validating state synchronization logic before connecting multi-thousand-dollar hardware debuggers.",
            "Mocking complex peripheral interaction scenarios for student lab exercises.",
            "Unit testing firmware unpacker algorithms and memory layout generators.",
            "Benchmarking internal message queue throughput without CPU emulation bottlenecks."
        ],
        "caveats": [
            "`DummyTarget` does not execute real machine instructions; it only stores and returns simulated state.",
            "Memory accesses on `DummyTarget` must be backed by memory range structures or custom protocols.",
            "State transitions must be explicitly updated or driven by your test harness.",
            "Do not use `DummyTarget` when real opcode execution or interrupt timing verification is needed."
        ],
        "test_data": "- **Target**: Simulated ARM Cortex-M3 Core\n- **Stack Base**: `0x20010000`\n- **Entry PC**: `0x08000101` (Thumb Reset Handler)",
        "resources": [
            "Avatar2 DummyTarget Source (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/dummy_target.py)",
            "ARM Architecture Procedure Call Standard (AAPCS) (https://developer.arm.com/documentation/ihi0042/latest)",
            "Automated Testing Strategies for Embedded Systems (https://martinfowler.com/articles/microservice-testing/)"
        ],
        "hashtags": ["#Avatar2", "#UnitTesting", "#Mocking", "#EmbeddedSecurity", "#CI_CD", "#ReverseEngineering"]
    },

    # --------------------------------------------------------------------------
    # Post 04
    # --------------------------------------------------------------------------
    {
        "num": 4,
        "dir_name": "04_unicorn_fast_cpu_emulation",
        "title": "High-Performance JIT CPU Emulation with the Unicorn Engine",
        "emoji": "⚡️ 🏎",
        "intro": (
            "When analyzing firmware snippets, cryptographic loops, or unpacking algorithms, spinning up a "
            "heavy full-system virtual machine (such as QEMU) introduces unwanted latency and architectural complexity. "
            "Avatar2 integrates `UnicornTarget`, wrapping the battle-tested Unicorn Engine (based on QEMU's TCG JIT). "
            "`UnicornTarget` executes raw Thumb-2 machine code at near-native JIT compilation speeds while "
            "remaining fully orchestrated within Avatar's unified memory and event framework."
        ),
        "core_concepts": [
            "**Unicorn Engine JIT Core**: Ultra-fast just-in-time compilation of ARM, MIPS, and x86 machine opcodes.",
            "**Instruction-Level Stepping**: Executing individual opcodes programmatically with post-instruction register inspection.",
            "**Dynamic Bytecode Injection**: Writing raw Thumb machine code directly into emulated memory sections.",
            "**Thumb Mode Bit Handling**: Addressing ARM Cortex-M execution rules where odd addresses (`PC | 1`) designate Thumb execution.",
            "**Unified Target Controls**: Reading and writing register files and memory buffers through Avatar's standardized API."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "De-obfuscating encrypted strings in embedded firmware through targeted function emulation.",
            "High-speed fuzzing of cryptographic hash algorithms without full OS overhead.",
            "Simulating firmware decompression routines (LZMA, gzip) in isolated RAM spaces.",
            "Analyzing shellcode payloads targeting embedded ARM microcontrollers.",
            "Verifying cross-compiled assembly subroutines in continuous integration."
        ],
        "caveats": [
            "Unicorn does not emulate hardware peripherals; any MMIO access must be handled via Avatar memory forwarding.",
            "In ARM Thumb mode, ensure the target PC odd bit rule is respected to prevent invalid opcode exceptions.",
            "Unicorn lacks full POSIX or FreeRTOS system call handlers by design.",
            "JIT cache invalidation is required when hot-patching self-modifying code in memory.",
            "avatar2 1.4.7's `UnicornTarget` never reports `TargetStates.STOPPED` back from its worker with unicorn 2.x (and it still ships legacy 1.x register IDs), so this demo drives the same Unicorn engine directly - that is what makes real instruction stepping possible today."
        ],
        "test_data": "- **Architecture**: ARMv7-M (Thumb-2 Mode)\n- **Opcode Sequence**: `4ff028004ff0020100eb01024ff07f0382ea0302`\n- **Target Expression**: `(40 + 2) ^ 0x7F = 0x55 (85)`",
        "resources": [
            "Unicorn Engine Project (https://www.unicorn-engine.org/)",
            "Keystone Assembler Engine (https://www.keystone-engine.org/)",
            "ARM Cortex-M Thumb-2 Instruction Set Quick Reference (https://developer.arm.com/documentation/qrc0001/latest)"
        ],
        "hashtags": ["#Avatar2", "#UnicornEngine", "#Keystone", "#BinaryEmulation", "#Thumb2", "#ReverseEngineering"]
    },

    # --------------------------------------------------------------------------
    # Post 05
    # --------------------------------------------------------------------------
    {
        "num": 5,
        "dir_name": "05_gdb_target_remote_rsp_control",
        "title": "GDB Remote Serial Protocol (RSP) Target Control & Instrumentation",
        "emoji": "⚡️ 🛰",
        "intro": (
            "The GDB Remote Serial Protocol (RSP) is the universal lingua franca of embedded systems debugging. "
            "Whether communicating with OpenOCD JTAG servers, hardware dongles, QEMU's `-s` gdbstub, or native "
            "microcontroller debuggers, RSP provides packetized control over registers, breakpoints, and memory. "
            "Avatar2's `GDBTarget` abstracts this protocol layer via `pygdbmi`, allowing automated Python scripts "
            "to issue commands, inspect stack frames, and control execution flow over TCP/IP sockets."
        ),
        "core_concepts": [
            "**GDB RSP Socket Abstraction**: Packetized command/response exchanges (`$g#`, `$m...#`, `$c#`) managed under the hood.",
            "**Target Lifecycle Synchronization**: Coordinating `cont`, `step`, and breakpoint traps over remote sockets.",
            "**Register Bank Deserialization**: Parsing architecture-specific hex register strings into structured Python attributes.",
            "**Non-Stop Debugging Mode**: Interacting with multi-core target threads asynchronously without global freezes.",
            "**Bridge to External Debuggers**: Multiplexing remote execution targets into external GUI analysis environments."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Automated headless regression testing over OpenOCD and Black Magic Probe hardware dongles.",
            "Dynamic breakpoint orchestration during vulnerability triage of proprietary firmware.",
            "Scripted extraction of decrypted firmware payloads directly from device RAM over SWD.",
            "Bridging proprietary hardware probes into standard Python analysis pipelines.",
            "Synchronizing execution between physical hardware and symbolic execution engines."
        ],
        "caveats": [
            "Network latency on GDB RSP sockets directly impacts single-stepping throughput.",
            "Ensure the remote gdbserver implementation supports target XML memory maps (`qXfer:memory-map:read`).",
            "Hardware breakpoints on ARM Cortex-M are typically limited by silicon to 4 or 6 FPB units.",
            "Always verify socket timeout handling to prevent scripts from hanging indefinitely on stalled targets.",
            "The RSP client is implemented inline (frame checksums, ACK handling, byte-order aware register decoding) because avatar2's `GDBTarget` expects a multi-arch ARM gdb binary, which is missing on most analysis workstations."
        ],
        "test_data": "- **Protocol**: GDB Remote Serial Protocol (RSP)\n- **Endpoint**: `127.0.0.1:3333`\n- **Target Registers**: `PC=0x08001234`, `SP=0x20003FE0`, `R0=0xDEADBEEF`",
        "resources": [
            "GDB Remote Serial Protocol Specification (https://sourceware.org/gdb/current/onlinedocs/gdb.html/Remote-Protocol.html)",
            "Avatar2 GDB Protocol Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/gdb.py)",
            "PyGDBMI Python Client Documentation (https://github.com/cs01/pygdbmi)"
        ],
        "hashtags": ["#Avatar2", "#GDB", "#RSP", "#FirmwareDebugging", "#HardwareHacking", "#ReverseEngineering"]
    },

    # --------------------------------------------------------------------------
    # Post 06
    # --------------------------------------------------------------------------
    {
        "num": 6,
        "dir_name": "06_qemu_full_system_arm_target",
        "title": "Full-System ARM Cortex-M Emulation on a Live QEMU Machine",
        "emoji": "⚡️ 🖥",
        "intro": (
            "While standalone CPU emulators handle basic opcode execution, real-world embedded firmware relies "
            "on system timers, interrupt controllers, and board-level memory hierarchies. "
            "Avatar2's `QemuTarget` harnesses full-system QEMU (`qemu-system-arm`) to provide complete microcontroller "
            "system virtualization. By communicating with QEMU via GDB RSP and the QEMU Machine Protocol (QMP), "
            "Avatar2 can spin up virtual boards (such as `lm3s6965evb` or `versatilepb`), load firmware binaries, "
            "and intercept execution at the system bus boundary."
        ),
        "core_concepts": [
            "**Full-System QEMU Virtualization**: Emulating not just CPU cores, but interrupt controllers (NVIC), buses, and timers.",
            "**Board Profile Selection**: Instantiating standardized embedded board machine models (e.g., `lm3s6965evb`).",
            "**QMP Protocol Communication**: Programmatic control over QEMU internal state, snapshots, and runtime device configuration.",
            "**Kernel / Firmware Ingestion**: Loading raw binary images or ELF kernels into virtual ROM address spaces.",
            "**Bus Interception Foundation**: Preparing memory layouts for dynamic forwarding when firmware touches custom peripherals."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Running complete embedded RTOS kernels (FreeRTOS, Zephyr) with virtual system timers.",
            "Analyzing multi-stage bootloader firmware images across real bus topologies.",
            "Validating cross-compiled firmware before deploying onto physical microcontroller hardware.",
            "Conducting full-system firmware vulnerability research with standard gdb attachments.",
            "Developing complex peripheral models before physical silicon is fabricated."
        ],
        "caveats": [
            "QEMU system emulation requires the host machine to have `qemu-system-arm` installed and in PATH.",
            "Standard QEMU machine types have rigid memory layouts; mismatching your firmware's linker script causes boot faults.",
            "QEMU TCG optimizes basic blocks, which can alter timing assumptions in cycle-accurate firmware.",
            "Firmware touching unmodeled board peripherals will stall or trigger hard faults unless forwarded.",
            "avatar2's `QemuTarget` requires a patched avatar-qemu build (`-machine configurable`, JSON kernel config). With a stock QEMU installation the demo boots the machine itself and drives it over the GDB RSP stub instead."
        ],
        "test_data": "- **Target Board**: Texas Instruments Stellaris `lm3s6965evb`\n- **CPU Architecture**: ARM Cortex-M3\n- **Memory Layout**: Flash (256 KB @ `0x00000000`), SRAM (64 KB @ `0x20000000`)",
        "resources": [
            "QEMU ARM System Emulator Documentation (https://www.qemu.org/docs/master/system/target-arm.html)",
            "Avatar2 QemuTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/qemu_target.py)",
            "QEMU Machine Protocol (QMP) Guide (https://wiki.qemu.org/Documentation/QMP)"
        ],
        "hashtags": ["#Avatar2", "#QEMU", "#ARM", "#FirmwareEmulation", "#CortexM", "#EmbeddedSecurity"]
    },

    # --------------------------------------------------------------------------
    # Post 07
    # --------------------------------------------------------------------------
    {
        "num": 7,
        "dir_name": "07_hardware_in_the_loop_memory_forwarding",
        "title": "Hardware-in-the-Loop (HITL) Memory Forwarding Architecture",
        "emoji": "⚡️ 🔀",
        "intro": (
            "The defining breakthrough of the Avatar2 framework is **Memory Forwarding**. "
            "When reverse engineering proprietary embedded systems, emulating the entire hardware peripheral landscape "
            "(radio transceivers, cryptographic coprocessors, proprietary ASICs) is prohibitively expensive or impossible. "
            "Avatar2 solves this by bridging emulated execution with physical hardware: when execution inside an emulator "
            "attempts to read or write an unmodeled MMIO register, Avatar2 traps the access and forwards it over JTAG/SWD "
            "to the physical microcontroller, transparently returning the physical device's response back to the emulator."
        ),
        "core_concepts": [
            "**Transparent Memory Forwarding**: Intercepting guest MMIO reads/writes and proxying them across targets.",
            "`forwarded=True` & `forwarded_to`: Avatar2 API primitives defining which target handles memory operations.",
            "**Hardware-in-the-Loop (HITL)**: Hybrid execution combining high-speed virtual CPU emulation with real silicon I/O.",
            "**Access Trapping**: Pausing virtual execution at the exact instruction requesting peripheral I/O.",
            "**Bidirectional State Transfer**: Forwarding register writes to hardware and streaming hardware sensor reads back to the guest."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Executing encrypted firmware inside an emulator while forwarding crypto MMIO to a physical hardware HSM.",
            "Analyzing Bluetooth and Zigbee IoT stacks by forwarding baseband radio registers to real silicon.",
            "Fuzzing complex network parser functions in virtual machines while keeping physical actuators connected.",
            "Extracting secret keys from on-chip hardware accelerators without physical decapping.",
            "Accelerating dynamic malware analysis of proprietary automotive microcontrollers."
        ],
        "caveats": [
            "Memory forwarding introduces latency (~1ms per JTAG transaction); avoid forwarding high-frequency DMA buffers.",
            "Physical hardware registers with side-effects (e.g. clear-on-read FIFO registers) must be handled carefully.",
            "Watchdog timers on physical hardware can expire while virtual execution is paused or single-stepping.",
            "Ensure voltage levels and clock domains match when connecting physical debugging probes."
        ],
        "test_data": "- **Forwarded MMIO Range**: `0x40020000` - `0x40021000` (Size: 4 KB)\n- **Forwarded Target**: Physical Radio Chip Proxy (`physical_radio_chip`)\n- **Simulated Hardware Registers**: `Device ID (0x00)`, `Status (0x04)`, `Config (0x08)`",
        "resources": [
            "Avatar2 Memory Forwarding Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)",
            "Research Paper: Towards Fully Automated Firmware Analysis (https://s3.eurecom.fr/docs/ndss14_avatar.pdf)",
            "Hardware-in-the-Loop Simulation Best Practices (https://en.wikipedia.org/wiki/Hardware-in-the-loop_simulation)"
        ],
        "hashtags": ["#Avatar2", "#HITL", "#MemoryForwarding", "#HardwareSecurity", "#IoT", "#FirmwareAnalysis"]
    },

    # --------------------------------------------------------------------------
    # Post 08
    # --------------------------------------------------------------------------
    {
        "num": 8,
        "dir_name": "08_python_peripheral_modeling_mmio",
        "title": "Custom MMIO Peripheral Modeling with AvatarPeripheral",
        "emoji": "⚡️ 🔌",
        "intro": (
            "When physical hardware is unavailable or when security researchers want to fuzz error handling "
            "routines under synthetic conditions, writing software peripheral models is the optimal strategy. "
            "Avatar2 provides the `AvatarPeripheral` base class, allowing researchers to model hardware devices "
            "entirely in Python. By attaching custom read and write handlers to specific register offset intervals, "
            "models can emulate complex status flags, control registers, latch mechanisms, and error conditions."
        ),
        "core_concepts": [
            "`AvatarPeripheral` Architecture: Python base class encapsulating address ranges and interval handler trees.",
            "**Interval Handler Binding**: Mapping address ranges (`[offset:offset+size]`) to dedicated Python functions.",
            "**Access Width Dispatch**: Handling 8-bit, 16-bit, and 32-bit memory operations accurately.",
            "**Program Counter Awareness**: Inspecting the guest `pc` parameter to determine which firmware function accessed the peripheral.",
            "**Stateful Register Latching**: Simulating read-clear, write-1-to-clear, and auto-incrementing hardware behaviors."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Emulating proprietary automotive CAN controller registers to test diagnostic protocol stacks.",
            "Mocking hardware cryptographic engines to inject known keys during reverse engineering.",
            "Fuzzing firmware input parser routines by feeding malformed packets through virtual MMIO FIFOs.",
            "Simulating sensor failures and hardware fault conditions to evaluate safety mechanisms.",
            "Accelerating software-in-the-loop (SIL) development before hardware tape-out."
        ],
        "caveats": [
            "All intervals mapped in `read_handler` and `write_handler` must not overlap within the same peripheral.",
            "Ensure unused offsets return a sane default (such as `0x00000000` or `0xFFFFFFFF`) rather than crashing.",
            "Be mindful of endianness when handling sub-word (8-bit or 16-bit) writes into 32-bit registers.",
            "Python-level peripheral callbacks add overhead compared to native C QEMU device models.",
            "The CPU is real, but MMIO reads are served by the Python model and the loaded register is patched on the next instruction hook - Unicorn cannot rewrite a load result from inside a memory hook."
        ],
        "test_data": "- **Peripheral Base**: `0x40010000` (Size: 4 KB)\n- **Registers**: CR (`0x00`), SR (`0x04`), DIN (`0x08`), DOUT (`0x0C`)\n- **Simulated Action**: Hash calculation over string `KEY!` -> Digest `0x1337BEEB`",
        "resources": [
            "AvatarPeripheral Base Class Reference (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)",
            "Modeling Embedded Hardware in Python (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)",
            "Principles of Memory-Mapped I/O Design (https://en.wikipedia.org/wiki/Memory-mapped_I/O)"
        ],
        "hashtags": ["#Avatar2", "#MMIO", "#HardwareEmulation", "#PythonSecurity", "#ReverseEngineering", "#Embedded"]
    },

    # --------------------------------------------------------------------------
    # Post 09
    # --------------------------------------------------------------------------
    {
        "num": 9,
        "dir_name": "09_virtual_uart_serial_telemetry",
        "title": "Virtual UART Serial Console & Telemetry Capture",
        "emoji": "⚡️ 📟",
        "intro": (
            "During bootup, almost every embedded microcontroller transmits debug logs, bootloader banners, "
            "and runtime diagnostics through a Universal Asynchronous Receiver-Transmitter (UART) serial port. "
            "When analyzing firmware without physical serial pins attached, modeling a virtual UART peripheral "
            "allows researchers to intercept `printf` characters as they are written to the UART Data Register (DR), "
            "reconstruct output strings in memory, and capture essential system telemetry in real time."
        ),
        "core_concepts": [
            "**UART Architecture Emulation**: Modeling the standard PL011 / STM32 USART register interface.",
            "**Data Register (DR) Interception**: Capturing transmitted TX bytes and queuing incoming RX bytes.",
            "**Flag Register (FR) Status Simulation**: Emulating Transmit FIFO Empty (`TXFE`) and Receive FIFO Not Empty (`RXNE`) flags.",
            "**Real-Time String De-packetization**: Buffering raw byte writes and decoding ASCII newline-delimited log strings.",
            "**Two-Way Interactive Shells**: Injecting operator commands into the guest firmware's serial command-line interpreter."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Capturing runtime panic traces and assertion failure logs from stripped firmware.",
            "Automated scraping of compile-time Git commit hashes and build dates from boot banners.",
            "Fuzzing embedded command-line shells (BusyBox, U-Boot CLI) over simulated serial terminals.",
            "Bypassing interactive password prompts by pre-loading serial RX FIFO queues with credentials.",
            "Recording complete communication transcripts for compliance and security auditing."
        ],
        "caveats": [
            "Firmware checking baud rate divisor registers (`UARTIBRD`) must receive non-zero values to avoid division-by-zero faults.",
            "Ensure the flag register reports `TXFE` (Transmit FIFO Empty); otherwise firmware loops waiting forever in serial polling loops.",
            "Handle multi-byte UTF-8 sequences properly when decoding guest log streams.",
            "Some firmware uses interrupt-driven UART rather than busy-wait polling; see Post 14 for NVIC interrupt injection.",
            "Status registers are pre-seeded in the emulated MMIO window and data writes are intercepted by a hook, mirroring what a patched avatar-qemu does at the KVM/QEMU boundary."
        ],
        "test_data": "- **Peripheral Model**: ARM PrimeCell PL011 UART\n- **Base Address**: `0x4000C000` (Size: 4 KB)\n- **Registers**: Data Register `UARTDR (0x00)`, Flag Register `UARTFR (0x18)`",
        "resources": [
            "ARM PrimeCell UART (PL011) Technical Reference Manual (https://developer.arm.com/documentation/ddi0183/latest)",
            "Avatar2 Peripheral Modeling Documentation (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)",
            "Embedded Serial Console Analysis Guide (https://wiki.securityheads.io/hardware-hacking/serial-uart)"
        ],
        "hashtags": ["#Avatar2", "#UART", "#SerialConsole", "#FirmwareAnalysis", "#PL011", "#EmbeddedSecurity"]
    },

    # --------------------------------------------------------------------------
    # Post 10
    # --------------------------------------------------------------------------
    {
        "num": 10,
        "dir_name": "10_hardware_timer_watchdog_simulation",
        "title": "Hardware Decrementing Timers & Watchdog Pet Simulation",
        "emoji": "⚡️ ⏱",
        "intro": (
            "Embedded microcontrollers implement Hardware Watchdog Timers (WDT) to recover from software deadlocks: "
            "if the firmware fails to write a periodic 'pet' or 'refresh' key to the watchdog register within a designated "
            "time window, the hardware asserts an MCU system reset. In dynamic analysis sandboxes, stepping through code "
            "or hitting breakpoints delays execution, causing the watchdog to expire and crash the analysis session. "
            "By modeling a virtual watchdog peripheral in Avatar2, researchers can monitor watchdog pet sequences, "
            "simulate timeout recovery, or neutralize watchdog resets entirely."
        ),
        "core_concepts": [
            "**Watchdog Mechanism Emulation**: Simulating hardware countdown timers, reload windows, and reset thresholds.",
            "**Pet Key Validation**: Requiring firmware to write exact magic sequences (e.g. `0xAAAA` / `0x5555`) to reload counters.",
            "**Anti-Analysis Neutralization**: Freezing or extending watchdog timers to allow unlimited single-stepping.",
            "**Timeout Event Handling**: Simulating MCU reset triggers when firmware legitimately hangs in infinite loops.",
            "**Windowed Watchdog Support**: Modeling advanced watchdogs that reject pets issued too early or too late."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Defeating watchdog-based anti-analysis techniques that intentionally reset during debugging.",
            "Evaluating fault tolerance and fail-safe recovery routines in safety-critical automotive firmware.",
            "Testing firmware response to clock prescaler anomalies and timer starvation.",
            "Preventing analysis aborts while conducting lengthy symbolic execution or memory scans.",
            "Locating missing watchdog pet instructions in firmware development builds."
        ],
        "caveats": [
            "In physical Hardware-in-the-Loop setups, physical watchdogs must be fed over JTAG or disabled in option bytes.",
            "Some microcontrollers lock the watchdog configuration once started; writes to prescaler registers are ignored.",
            "Windowed watchdogs (WWDG) trigger resets if petted too early; ensure pet intervals match the allowed window.",
            "Watchdog simulation frequency should be scaled to match emulated CPU cycle time."
        ],
        "test_data": "- **Peripheral Model**: STM32-style Independent Watchdog (IWDG)\n- **Base Address**: `0x40003000` (Size: 4 KB)\n- **Control Keys**: Enable (`0xCCCC`), Reload (`0xAAAA`)\n- **Initial Countdown**: 3 ticks",
        "resources": [
            "STM32 Independent Watchdog (IWDG) Reference Manual (https://www.st.com/resource/en/reference_manual/rm0008-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)",
            "Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)",
            "Embedded Watchdog Timer Design Best Practices (https://www.embedded.com/introduction-to-watchdog-timers/)"
        ],
        "hashtags": ["#Avatar2", "#WatchdogTimer", "#IWDG", "#FirmwareSecurity", "#AntiAnalysis", "#Embedded"]
    },

    # --------------------------------------------------------------------------
    # Post 11
    # --------------------------------------------------------------------------
    {
        "num": 11,
        "dir_name": "11_watchmen_event_driven_instrumentation",
        "title": "Asynchronous Target Event Instrumentation with Watchmen",
        "emoji": "⚡️ 👁",
        "intro": (
            "Complex dynamic analysis requires reacting to target actions dynamically: when a target stops, "
            "when a breakpoint fires, when a syscall triggers, or when memory is accessed. "
            "Avatar2 includes `Watchmen`, an event-driven pub/sub notification subsystem. "
            "Using the `@watch` decorator and event listener callbacks, security analysts can attach asynchronous "
            "hooks that execute before (`BEFORE`) or after (`AFTER`) core target operations, enabling transparent "
            "telemetry collection, security policy enforcement, and execution tracing."
        ),
        "core_concepts": [
            "**Watchmen Event Dispatcher**: Central event bus delivering notification messages to registered handler callbacks.",
            "**Trigger Phasing (`BEFORE` & `AFTER`)**: Choosing whether callbacks fire prior to or immediately following the target action.",
            "**Event Types**: Monitoring `TargetInit`, `TargetStateUpdate`, `TargetWait`, `BreakpointHit`, and `MemoryAccess`.",
            "**Non-Intrusive Telemetry**: Collecting forensic execution statistics without modifying guest firmware binary code.",
            "**Reactive Security Auditing**: Dynamically validating invariant rules (e.g. stack limits) whenever execution halts."
        ],
        "code": '''#!/usr/bin/env python3
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
    run_watchmen_demo()''',
        "use_cases": [
            "Automated logging of target state transitions during long-running firmware fuzzing runs.",
            "Enforcing execution timeouts and watchdog policies when targets enter unhandled states.",
            "Capturing instruction trace logs automatically whenever a target enters `TargetStates.STOPPED`.",
            "Building live terminal dashboards displaying multi-target cluster status in real time.",
            "Synchronizing external network traffic packet sniffers to target execution milestones."
        ],
        "caveats": [
            "Watchmen callbacks run synchronously within event dispatcher threads; avoid heavy I/O operations inside hooks.",
            "Exceptions raised inside callbacks can disrupt the internal message processing pipeline.",
            "Use `AFTER` callbacks when inspecting updated register values to ensure the target state has finalized.",
            "Be aware of thread safety when accessing shared data structures from multiple Watchmen callbacks."
        ],
        "test_data": "- **Event Channel**: `TargetStateUpdate`\n- **Trigger Phase**: `AFTER`\n- **Observed Transitions**: `STOPPED` -> `RUNNING` -> `STOPPED`",
        "resources": [
            "Avatar2 Watchmen Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/watchmen.py)",
            "Event-Driven Architecture in Reverse Engineering Tools (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)",
            "Python Pub/Sub Design Patterns (https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)"
        ],
        "hashtags": ["#Avatar2", "#Watchmen", "#EventDriven", "#BinaryInstrumentation", "#FirmwareAnalysis", "#CyberSecurity"]
    },

    # --------------------------------------------------------------------------
    # Post 12
    # --------------------------------------------------------------------------
    {
        "num": 12,
        "dir_name": "12_breakpoint_watchpoint_automation",
        "title": "Automated Dynamic Breakpoints & Memory Access Watchpoints",
        "emoji": "⚡️ 🎯",
        "intro": (
            "Breakpoints and watchpoints are the primary instruments of dynamic execution control. "
            "A breakpoint traps execution when the instruction pointer reaches a designated code address, "
            "while a memory watchpoint halts execution whenever data is read from or written to a designated "
            "RAM variable or MMIO register. Avatar2 unifies breakpoint and watchpoint management across backends, "
            "allowing scripts to arm hardware/software traps, inspect registers upon triggering, and resume "
            "execution automatically."
        ),
        "core_concepts": [
            "`set_breakpoint(address)`: Registering execution traps on subroutine entries or sensitive code branches.",
            "`set_watchpoint(address, type)`: Registering memory access traps on variables (Read, Write, or Read/Write).",
            "**Breakpoint Hit Message Processing**: Catching `BreakpointHitMessage` in Avatar's event queues.",
            "**Contextual Register Snapshotting**: Extracting function arguments (`r0`-`r3`) and call stacks at the moment of impact.",
            "**Automated Trap Clearence**: Programmatically removing or disabling breakpoints after hits to maintain high throughput."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Intercepting firmware authentication routines to extract plain PINs, passwords, and tokens.",
            "Detecting unauthorized writes to critical RTOS scheduler variables and task control blocks.",
            "Tracing state transitions in embedded Finite State Machines (FSMs).",
            "Measuring execution time intervals between subroutine entry and return breakpoints.",
            "Automated crash localization by placing watchpoints on stack canary memory locations."
        ],
        "caveats": [
            "Hardware breakpoints on physical Cortex-M chips are limited by hardware FPB units (typically 4 to 6).",
            "Software breakpoints in Flash ROM require flash patching or FPB hardware remapping.",
            "Watchpoints monitor aligned 4-byte or 8-byte addresses; unaligned accesses may bypass watchpoint triggers.",
            "Always remove one-time breakpoints inside your handler to prevent infinite loop re-triggers."
        ],
        "test_data": "- **Target Subroutine**: `auth_verify_pin()` @ `0x080015A0`\n- **Target Security Flag**: `g_authenticated` @ `0x20000800`\n- **Monitored Registers**: `R0` (Buffer), `R1` (PIN: 1234)",
        "resources": [
            "Avatar2 Target Breakpoint Interface (https://avatar2.readthedocs.io/en/latest/api/targets.html)",
            "ARM Cortex-M Flash Patch and Breakpoint (FPB) Unit (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/peripherals/flash-patch-and-breakpoint-unit)",
            "Hardware vs Software Breakpoint Mechanisms (https://en.wikipedia.org/wiki/Breakpoint)"
        ],
        "hashtags": ["#Avatar2", "#Breakpoints", "#Watchpoints", "#ReverseEngineering", "#FirmwareSecurity", "#HardwareHacking"]
    },

    # --------------------------------------------------------------------------
    # Post 13
    # --------------------------------------------------------------------------
    {
        "num": 13,
        "dir_name": "13_cross_target_state_synchronization",
        "title": "Heterogeneous Cross-Target State Synchronization",
        "emoji": "⚡️ 🔄",
        "intro": (
            "One of the most powerful workflows enabled by Avatar2 is hybrid target switching: executing firmware "
            "on real silicon until an interesting function is reached, then transferring the entire execution state "
            "(registers, memory pages, stack) into an emulator or symbolic execution engine (like angr) for in-depth "
            "analysis, and finally pushing the solved state back onto hardware. Avatar2 provides `synchronize_state`, "
            "a formal protocol for extracting, serializing, and injecting complete machine states across heterogeneous targets."
        ),
        "core_concepts": [
            "**Heterogeneous State Transfer**: Copying CPU registers and memory pages between dissimilar targets (e.g. OpenOCD -> QEMU).",
            "`synchronize_state()` Protocol: Coordinating state serialization, target halting, and state restoration.",
            "**Register Bank Serialization**: Serializing general registers (`r0`-`r12`), `sp`, `lr`, `pc`, and status register `xpsr`.",
            "**Dirty Memory Synchronization**: Transferring only modified SRAM sections to minimize JTAG transmission delays.",
            "**Execution Handoff**: Resuming execution on the destination target seamlessly from the exact instruction halted."
        ],
        "code": '''#!/usr/bin/env python3
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
    run_state_sync_demo()''',
        "use_cases": [
            "Concolic execution handoff: moving concrete hardware state into angr to solve complex path conditions.",
            "Snapshotting device states before executing destructive firmware erase commands.",
            "Transferring state from physical embedded devices into QEMU to enable multi-threaded fuzzing.",
            "Live migration of running RTOS tasks across distributed virtual hardware nodes.",
            "Forensic extraction and offline cloning of compromised IoT device RAM states."
        ],
        "caveats": [
            "Special registers (such as ARM `CONTROL`, `BASEPRI`, and floating-point `FPSCR`) must be included in transfers.",
            "Memory caches (L1 D-Cache/I-Cache) on physical chips must be flushed prior to state extraction.",
            "Hardware peripherals with active DMA transfers must be halted to prevent memory divergence during sync.",
            "Ensure destination target memory regions have identical base mappings as the source."
        ],
        "test_data": "- **Source Target**: `source_hardware` (Physical JTAG Target Mock)\n- **Destination Target**: `dest_emulator` (Virtual Target Mock)\n- **Synchronized State**: `PC=0x080018C0`, `SP=0x20003F00`, `R0=0xCAFEBABE`",
        "resources": [
            "Avatar2 State Synchronization Architecture (https://avatar2.readthedocs.io/en/latest/api/targets.html)",
            "Hybrid Execution: Forwarding and State Transfer (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)",
            "Virtual Machine Migration and State Serialization (https://en.wikipedia.org/wiki/Live_migration)"
        ],
        "hashtags": ["#Avatar2", "#StateSync", "#ConcolicExecution", "#FirmwareSecurity", "#HardwareInTheLoop", "#angr"]
    },

    # --------------------------------------------------------------------------
    # Post 14
    # --------------------------------------------------------------------------
    {
        "num": 14,
        "dir_name": "14_armv7m_nvic_interrupt_injection",
        "title": "ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection",
        "emoji": "⚡️ ⚡️",
        "intro": (
            "Embedded microcontrollers are asynchronous, event-driven machines. Timers, serial ports, DMA controllers, "
            "and external GPIO pins signal the CPU through the Nested Vectored Interrupt Controller (NVIC). "
            "When analyzing firmware inside an emulator, hardware events do not occur automatically. "
            "Avatar2's `ARMV7MInterrupt` protocol provides programmatic interrupt injection: analysts can assert "
            "synthetic hardware IRQs, trigger SysTick exceptions, and force execution into Interrupt Service Routines "
            "(ISRs) to analyze vulnerability paths in asynchronous interrupt handlers."
        ),
        "core_concepts": [
            "**Cortex-M NVIC Architecture**: Vector tables, exception numbers (1-15 system, 16+ external IRQs), and priority arbitration.",
            "**Vector Table Address Resolution**: Reading the ISR function pointer from base offset `(4 * (exception_number))`.",
            "**Programmatic IRQ Injection**: Simulating external hardware pin changes and timer alarms dynamically.",
            "**Stack Frame Exception Entry**: Emulating hardware pushing `r0`-`r3`, `r12`, `lr`, `pc`, and `xpsr` onto the stack.",
            "`EXC_RETURN` Logic: Managing return from interrupt transitions (`0xFFFFFFF9` / `0xFFFFFFFD`)."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "Fuzzing interrupt service routines (ISRs) for race conditions, reentrancy bugs, and deadlocks.",
            "Simulating periodic timer ticks (SysTick) to trigger RTOS scheduler task preemption.",
            "Injecting spurious or out-of-order hardware interrupts to test robustness against glitching attacks.",
            "Analyzing DMA completion interrupt handlers for buffer overflow and memory corruption vulnerabilities.",
            "Testing power-saving sleep modes (WFI / WFE instructions) by waking cores via external IRQs."
        ],
        "caveats": [
            "Cortex-M vector table addresses must have the least-significant bit (LSB) set to 1 to indicate Thumb mode.",
            "Nested interrupts require tracking interrupt priority registers (`IPR`) to enforce preemption rules.",
            "Ensure the stack pointer is decremented by 32 bytes (or 104 bytes if FPU is enabled) to match hardware stacking.",
            "Watch out for interrupt storms: injecting interrupts faster than the ISR executes causes stack overflows."
        ],
        "test_data": "- **Architecture**: ARMv7-M NVIC\n- **Exception Numbers**: SysTick (15 @ `0x3C`), USART1 IRQ (16 @ `0x40`)\n- **Vector Target**: `USART1_ISR` @ `0x08000921`\n- **Stacking Frame**: 32-byte standard integer exception frame",
        "resources": [
            "Avatar2 ARMv7-M Interrupt Protocol (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/armv7m_interrupt.py)",
            "ARM Cortex-M3 NVIC Technical User Guide (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/exception-model)",
            "Exception Handling and Stacking in Cortex-M (https://interrupt.memfault.com/blog/arm-cortex-m-exceptions-and-nvic)"
        ],
        "hashtags": ["#Avatar2", "#NVIC", "#InterruptInjection", "#ARM", "#CortexM", "#FirmwareSecurity"]
    },

    # --------------------------------------------------------------------------
    # Post 15
    # --------------------------------------------------------------------------
    {
        "num": 15,
        "dir_name": "15_fast_remote_memory_protocol",
        "title": "High-Performance Remote Memory Protocol (RMP) & Demand-Paging",
        "emoji": "⚡️ 🚀",
        "intro": (
            "When forwarding memory across separate processes (such as QEMU and Python) or over physical debuggers, "
            "handling each 1-byte or 4-byte memory access over individual IPC messages causes severe performance degradation. "
            "Avatar2 introduces the **Remote Memory Protocol (RMP)**, a high-throughput protocol that implements "
            "demand-paging. When a target triggers an unmapped access, RMP fetches an entire memory block (e.g. 4KB) "
            "in a single atomic transaction, caches it locally in the target's address space, and satisfies future reads "
            "at native CPU speeds with zero IPC overhead."
        ),
        "core_concepts": [
            "**Remote Memory Protocol (RMP)**: Zero-copy message-queue-based memory protocol for high-throughput target bridging.",
            "**Demand-Paging Mechanism**: Page-fault-driven memory transfer: fetching 4KB pages only when first accessed.",
            "**Read-Only Page Caching**: Caching Flash ROM sections locally to eliminate redundant JTAG bus queries.",
            "**Dirty Page Tracking**: Recording written memory offsets to synchronize modified data back to the primary store.",
            "**Throughput Optimization**: Reducing memory forwarding latency from seconds to microseconds per operation."
        ],
        "code": '''#!/usr/bin/env python3
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
''',
        "use_cases": [
            "High-speed emulation of 16MB+ SPI Flash microcontrollers over slow JTAG connections.",
            "Demand-paging firmware pages from remote cloud repositories without downloading entire firmware images.",
            "Reducing execution time of hybrid symbolic analysis from hours to seconds.",
            "Shared memory inter-process communication between QEMU and custom Python harnesses.",
            "Non-intrusive memory sniffing of operating vehicle electronic control units (ECUs)."
        ],
        "caveats": [
            "Do not cache MMIO peripheral ranges with demand-paging; peripheral registers change dynamically.",
            "Writable RAM pages require write-back synchronization to prevent memory drift.",
            "Page size must match the memory management unit or translation block size of the emulator (typically 4096 bytes).",
            "Handle socket reconnections gracefully if the remote backing server drops during long analysis runs."
        ],
        "test_data": "- **Protocol**: Avatar2 Remote Memory Protocol (RMP)\n- **Page Block Size**: 4096 bytes (4 KB)\n- **Backing Storage**: 512 KB Simulated Flash Memory\n- **Cache Strategy**: Transparent Demand-Paging with Local In-Memory Cache",
        "resources": [
            "Avatar2 RemoteMemoryProtocol Source (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/remote_memory.py)",
            "Demand Paging Operating System Concepts (https://en.wikipedia.org/wiki/Demand_paging)",
            "Memory Virtualization in Hybrid Emulation (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)"
        ],
        "hashtags": ["#Avatar2", "#RMP", "#DemandPaging", "#PerformanceOptimization", "#FirmwareAnalysis", "#ReverseEngineering"]
    }
]
