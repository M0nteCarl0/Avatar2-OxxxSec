# ⚡️ ⚡️ ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection with Avatar2 Framework (Python practice)
_Post 14/30 · Avatar2 firmware orchestration playbook_

Embedded microcontrollers are asynchronous, event-driven machines. Timers, serial ports, DMA controllers, and external GPIO pins signal the CPU through the Nested Vectored Interrupt Controller (NVIC). When analyzing firmware inside an emulator, hardware events do not occur automatically.

## 🧠 Core Concept
- **Cortex-M NVIC Architecture**: Vector tables, exception numbers (1-15 system, 16+ external IRQs), and priority arbitration.
- **Vector Table Address Resolution**: Reading the ISR function pointer from base offset `(4 * (exception_number))`.
- **Programmatic IRQ Injection**: Simulating external hardware pin changes and timer alarms dynamically.
- **Stack Frame Exception Entry**: Emulating hardware pushing `r0`-`r3`, `r12`, `lr`, `pc`, and `xpsr` onto the stack.
- `EXC_RETURN` Logic: Managing return from interrupt transitions (`0xFFFFFFF9` / `0xFFFFFFFD`).

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
nvic = VirtualNvic("nvic", NVIC_BASE, NVIC_SIZE)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
```

## 🔥 Use Cases
- Fuzzing interrupt service routines (ISRs) for race conditions, reentrancy bugs, and deadlocks.
- Simulating periodic timer ticks (SysTick) to trigger RTOS scheduler task preemption.
- Injecting spurious or out-of-order hardware interrupts to test robustness against glitching attacks.
- Analyzing DMA completion interrupt handlers for buffer overflow and memory corruption vulnerabilities.
- Testing power-saving sleep modes (WFI / WFE instructions) by waking cores via external IRQs.

## ⚠️ Caveats
- Cortex-M vector table addresses must have the least-significant bit (LSB) set to 1 to indicate Thumb mode.
- Nested interrupts require tracking interrupt priority registers (`IPR`) to enforce preemption rules.
- Ensure the stack pointer is decremented by 32 bytes (or 104 bytes if FPU is enabled) to match hardware stacking.
- Watch out for interrupt storms: injecting interrupts faster than the ISR executes causes stack overflows.

## 📦 Target
- **Architecture**: ARMv7-M NVIC
- **Exception Numbers**: SysTick (15 @ `0x3C`), USART1 IRQ (16 @ `0x40`)
- **Vector Target**: `USART1_ISR` @ `0x08000921`
- **Stacking Frame**: 32-byte standard integer exception frame

## 🔗 Resources
- Avatar2 ARMv7-M Interrupt Protocol (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/armv7m_interrupt.py)
- ARM Cortex-M3 NVIC Technical User Guide (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/exception-model)
- Exception Handling and Stacking in Cortex-M (https://interrupt.memfault.com/blog/arm-cortex-m-exceptions-and-nvic)

**Runnable source, run log & report**: [`14_armv7m_nvic_interrupt_injection`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/14_armv7m_nvic_interrupt_injection)

#Avatar2 #NVIC #InterruptInjection #ARM #CortexM #FirmwareSecurity
