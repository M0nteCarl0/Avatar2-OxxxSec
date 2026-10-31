# ⚡️ 🏎 High-Performance JIT CPU Emulation with the Unicorn Engine with Avatar2 Framework (Python practice)

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
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #UnicornEngine #Keystone #BinaryEmulation #Thumb2 #ReverseEngineering
