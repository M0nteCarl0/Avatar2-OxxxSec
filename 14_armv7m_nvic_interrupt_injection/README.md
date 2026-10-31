# ⚡️ ⚡️ ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection with Avatar2 Framework (Python practice)

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
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #NVIC #InterruptInjection #ARM #CortexM #FirmwareSecurity
