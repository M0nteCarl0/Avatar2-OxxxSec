# ⚡️ 🩹 Dynamic Binary Patching & Hot-Patching Firmware in Memory (Python practice)

During security research, firmware frequently halts because of digital signature checks, hardware presence checks, or anti-tamper routines. Re-compiling or modifying the flash image file is often impractical when analyzing stripped or signed binaries.

## 🧠 Core Concept
- **In-Memory Hot-Patching**: Modifying executable machine code directly in target memory at runtime.
- **Opcode Assembly with Keystone**: Compiling assembly directives (`nop`, `b`, `movs r0, #1`) into Thumb bytecode.
- **Branch Neutralization**: Overwriting conditional branch instructions (`cbz`, `cbnz`, `beq`, `bne`) with `NOP`s.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 23: Dynamic Binary Patching & Hot-Patching Firmware in Memory.
Uses Keystone and Avatar2 memory primitives to disable an auth check at runtime."""

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

CHECK_ADDR = 0x080012A4


class EmulatedTarget(DummyTarget):
    """Target stand-in with a register file and a writable code window."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()
        self.patched = b""

    def write_memory(self, address, size, value, num_words=1, raw=False):
        self.patched = value.to_bytes(size, "little")
        return True


def run_hot_patching_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="patched_mcu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="flash_code", permissions="rwx")
    ava.init_targets()

    target.regs.pc, target.regs.r0 = CHECK_ADDR, 0xFFFFFFFF   # signature check failed
    print(f"[!] at check: PC=0x{target.regs.pc:08x} R0=0x{target.regs.r0:08x} [FAIL]")

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    patch, _ = ks.asm("nop; nop")                             # no-op sled over the branch
    target.write_memory(CHECK_ADDR, len(patch), int.from_bytes(bytes(patch), "little"))
    print(f"[+] patched 0x{CHECK_ADDR:08x} <- {target.patched.hex().upper()}")

    target.regs.r0 = 0x00000000                               # continue as if valid
    target.regs.pc += len(patch)
    print(f"[+] bypassed: PC=0x{target.regs.pc:08x} R0=0x{target.regs.r0:08x} [VALID]")
    ava.shutdown()


if __name__ == "__main__":
    run_hot_patching_demo()
```

## 🔥 Use Cases
- Bypassing hardware signature verification in firmware bootloaders during vulnerability research.
- Neutralizing anti-debugging timing loops without modifying original on-disk firmware files.
- Injecting custom telemetry hooks (trampolines) into stripped binary functions.

## ⚠️ Caveats & Responsible Practice
- In Thumb mode, instructions can be 16-bit or 32-bit; ensure patch sizes match the original instruction length.
- Branch instructions (`B`, `BL`) use relative PC offsets; calculating jump targets manually requires accounting for Thumb pipelining (`PC + 4`).

## 📦 Test Data & Sample Binaries
- **Target Instruction**: `BNE signature_failure` @ `0x080012A4`
- **Replacement Patch**: `NOP; NOP` (`0xBF00BF00`)
- **Assembler**: Keystone Assembler (ARM Thumb Mode)

## 🔗 Resources
- Keystone Assembler Documentation (https://www.keystone-engine.org/docs/)
- ARMv7-M Architecture Reference Manual (https://developer.arm.com/documentation/ddi0403/latest)

**Full script, run log & report**: [`23_dynamic_code_patching_hijacking/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/23_dynamic_code_patching_hijacking)

#Avatar2 #BinaryPatching #HotPatching #Keystone #Thumb2 #ReverseEngineering #FirmwareSecurity
