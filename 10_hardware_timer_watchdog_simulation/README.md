# ⚡️ ⏱ Hardware Decrementing Timers & Watchdog Pet Simulation with Avatar2 Framework (Python practice)
_Post 10/30 · Avatar2 firmware orchestration playbook_

Embedded microcontrollers implement Hardware Watchdog Timers (WDT) to recover from software deadlocks: if the firmware fails to write a periodic 'pet' or 'refresh' key to the watchdog register within a designated time window, the hardware asserts an MCU system reset. In dynamic analysis sandboxes, stepping through code or hitting breakpoints delays execution, causing the watchdog to expire and crash the analysis session.

## 🧠 Core Concept
- **Watchdog Mechanism Emulation**: Simulating hardware countdown timers, reload windows, and reset thresholds.
- **Pet Key Validation**: Requiring firmware to write exact magic sequences (e.g. `0xAAAA` / `0x5555`) to reload counters.
- **Anti-Analysis Neutralization**: Freezing or extending watchdog timers to allow unlimited single-stepping.
- **Timeout Event Handling**: Simulating MCU reset triggers when firmware legitimately hangs in infinite loops.
- **Windowed Watchdog Support**: Modeling advanced watchdogs that reject pets issued too early or too late.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cortex_m3")
target.update_state(TargetStates.STOPPED)
wdt = VirtualWatchdogTimer("iwdg", WDT_BASE, WDT_SIZE, initial_ticks=3)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
uc.mem_map(WDT_BASE, WDT_SIZE)
uc.mem_write(FLASH_BASE, assemble_firmware())
```

## 🔥 Use Cases
- Defeating watchdog-based anti-analysis techniques that intentionally reset during debugging.
- Evaluating fault tolerance and fail-safe recovery routines in safety-critical automotive firmware.
- Testing firmware response to clock prescaler anomalies and timer starvation.
- Preventing analysis aborts while conducting lengthy symbolic execution or memory scans.
- Locating missing watchdog pet instructions in firmware development builds.

## ⚠️ Caveats
- In physical Hardware-in-the-Loop setups, physical watchdogs must be fed over JTAG or disabled in option bytes.
- Some microcontrollers lock the watchdog configuration once started; writes to prescaler registers are ignored.
- Windowed watchdogs (WWDG) trigger resets if petted too early; ensure pet intervals match the allowed window.
- Watchdog simulation frequency should be scaled to match emulated CPU cycle time.

## 📦 Target
- **Peripheral Model**: STM32-style Independent Watchdog (IWDG)
- **Base Address**: `0x40003000` (Size: 4 KB)
- **Control Keys**: Enable (`0xCCCC`), Reload (`0xAAAA`)
- **Initial Countdown**: 3 ticks

## 🔗 Resources
- STM32 Independent Watchdog (IWDG) Reference Manual (https://www.st.com/resource/en/reference_manual/rm0008-stm32f101xx-stm32f102xx-stm32f103xx-stm32f105xx-and-stm32f107xx-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Embedded Watchdog Timer Design Best Practices (https://www.embedded.com/introduction-to-watchdog-timers/)

**Runnable source, run log & report**: [`10_hardware_timer_watchdog_simulation`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/10_hardware_timer_watchdog_simulation)

#Avatar2 #WatchdogTimer #IWDG #FirmwareSecurity #AntiAnalysis #Embedded
