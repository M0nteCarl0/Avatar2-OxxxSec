# ⚡️ ⏱ Hardware Decrementing Timers & Watchdog Pet Simulation (Python practice)

Embedded microcontrollers implement Hardware Watchdog Timers (WDT) to recover from software deadlocks: if the firmware fails to write a periodic 'pet' or 'refresh' key to the watchdog register within a designated time window, the hardware asserts an MCU system reset.

## 🧠 Core Concept
- **Watchdog Mechanism Emulation**: Simulating hardware countdown timers, reload windows, and reset thresholds.
- **Pet Key Validation**: Requiring firmware to write exact magic sequences (e.g. `0xAAAA` / `0x5555`) to reload counters.
- **Anti-Analysis Neutralization**: Freezing or extending watchdog timers to allow unlimited single-stepping.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 10: Hardware Decrementing Timers & Watchdog Pet Simulation.
Firmware pets a modeled IWDG, then deadlocks - the watchdog expires."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

WDT_BASE, WDT_SIZE = 0x40003000, 0x1000
TICK_PERIOD, EMU_BUDGET = 40, 3000     # 1 watchdog tick per 40 instructions


class VirtualWatchdogTimer(AvatarPeripheral):
    def __init__(self, name, address, size, max_ticks=3):
        super().__init__(name, address, size)
        self.counter = max_ticks
        self.enabled = self.reset_triggered = False
        self.pets_count = 0

    def write(self, offset, size, value):
        if offset == 0x00 and value == 0xCCCC:       # KR: start the watchdog
            self.enabled = True
        elif offset == 0x04:                         # RLR: pet it
            self.counter, self.pets_count = value, self.pets_count + 1
        return True

    def tick(self):                                  # emulation clock tick
        if self.enabled and not self.reset_triggered:
            self.counter -= 1
            self.reset_triggered = self.counter <= 0


def run_watchdog_simulation_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cortex_m3")
    target.update_state(TargetStates.STOPPED)
    wdt = VirtualWatchdogTimer("iwdg", WDT_BASE, WDT_SIZE, max_ticks=3)
    ava.add_memory_range(WDT_BASE, WDT_SIZE, name="wdt_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=wdt)
    ava.init_targets()

    wdt.write(0x00, 4, 0xCCCC)                      # firmware starts the IWDG,
    wdt.write(0x04, 4, 3)                           # pets it once, then deadlocks
    for _ in range(EMU_BUDGET // TICK_PERIOD):
        wdt.tick()
    print(f"[+] pets={wdt.pets_count} counter={wdt.counter} "
          f"reset={wdt.reset_triggered}")
    ava.shutdown()


if __name__ == "__main__":
    run_watchdog_simulation_demo()
```

## 🔥 Use Cases
- Defeating watchdog-based anti-analysis techniques that intentionally reset during debugging.
- Evaluating fault tolerance and fail-safe recovery routines in safety-critical automotive firmware.

## ⚠️ Caveats & Responsible Practice
- In physical Hardware-in-the-Loop setups, physical watchdogs must be fed over JTAG or disabled in option bytes.
- Some microcontrollers lock the watchdog configuration once started; writes to prescaler registers are ignored.

## 📦 Test Data & Sample Binaries
- **Peripheral Model**: STM32-style Independent Watchdog (IWDG)
- **Base Address**: `0x40003000` (Size: 4 KB)
- **Control Keys**: Enable (`0xCCCC`), Reload (`0xAAAA`)
- **Initial Countdown**: 3 ticks

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #WatchdogTimer #IWDG #FirmwareSecurity #AntiAnalysis #Embedded
