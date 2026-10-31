# ⚡️ ⏱ Hardware Decrementing Timers & Watchdog Pet Simulation with Avatar2 Framework (Python practice)

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
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #WatchdogTimer #IWDG #FirmwareSecurity #AntiAnalysis #Embedded
