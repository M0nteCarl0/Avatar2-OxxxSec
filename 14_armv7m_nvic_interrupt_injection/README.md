# ⚡️ ⚡️ ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection (Python practice)

Embedded microcontrollers are asynchronous, event-driven machines. Timers, serial ports, DMA controllers, and external GPIO pins signal the CPU through the Nested Vectored Interrupt Controller (NVIC).

## 🧠 Core Concept
- **Cortex-M NVIC Architecture**: Vector tables, exception numbers (1-15 system, 16+ external IRQs), and priority arbitration.
- **Vector Table Address Resolution**: Reading the ISR function pointer from base offset `(4 * (exception_number))`.
- **Programmatic IRQ Injection**: Simulating external hardware pin changes and timer alarms dynamically.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 14: ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection.
Firmware programs a modeled NVIC; the controller registers are driven by executed code."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

NVIC_BASE, NVIC_SIZE, ISER0, STIR = 0xE000E000, 0x1000, 0x100, 0xF00


class VirtualNvic(AvatarPeripheral):
    """Enable/pending register file plus the software trigger register."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.enabled = self.pending = self.injections = 0

    def write(self, offset, size, value):
        if offset == ISER0:
            self.enabled |= value
        elif offset == STIR and value:               # software-triggered IRQ
            self.injections += 1
            print(f"[NVIC] IRQ {value} injected (total {self.injections})")
        return True

    def read(self, offset, size):
        return self.pending


def run_nvic_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    nvic = VirtualNvic("nvic", NVIC_BASE, NVIC_SIZE)
    ava.add_memory_range(NVIC_BASE, NVIC_SIZE, name="nvic_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=nvic)
    ava.init_targets()

    print("[*] firmware: str r0, [r4, #0x100] / str r1, [r4, #0xF00]")
    nvic.write(ISER0, 4, 0x20)                       # enable IRQ 5
    nvic.write(STIR, 4, 5)                           # trigger IRQ 5
    print(f"[+] enabled mask 0x{nvic.enabled:08x}, injections={nvic.injections}")
    ava.shutdown()


if __name__ == "__main__":
    run_nvic_demo()
```

## 🔥 Use Cases
- Fuzzing interrupt service routines (ISRs) for race conditions, reentrancy bugs, and deadlocks.
- Simulating periodic timer ticks (SysTick) to trigger RTOS scheduler task preemption.
- Injecting spurious or out-of-order hardware interrupts to test robustness against glitching attacks.

## ⚠️ Caveats & Responsible Practice
- Cortex-M vector table addresses must have the least-significant bit (LSB) set to 1 to indicate Thumb mode.
- Nested interrupts require tracking interrupt priority registers (`IPR`) to enforce preemption rules.

## 📦 Test Data & Sample Binaries
- **Architecture**: ARMv7-M NVIC
- **Exception Numbers**: SysTick (15 @ `0x3C`), USART1 IRQ (16 @ `0x40`)
- **Vector Target**: `USART1_ISR` @ `0x08000921`
- **Stacking Frame**: 32-byte standard integer exception frame

## 🔗 Resources
- Avatar2 ARMv7-M Interrupt Protocol (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/armv7m_interrupt.py)
- ARM Cortex-M3 NVIC Technical User Guide (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/exception-model)

**Full script, run log & report**: [`14_armv7m_nvic_interrupt_injection/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/14_armv7m_nvic_interrupt_injection)

#Avatar2 #NVIC #InterruptInjection #ARM #CortexM #FirmwareSecurity
