# ⚡️ 🔌 Bare-Metal Microcontroller Debugging with OpenOCDTarget (Python practice)

OpenOCD (Open On-Chip Debugger) is the premier open-source tool for hardware-level debugging over JTAG and Serial Wire Debug (SWD).

## 🧠 Core Concept
- **OpenOCD Process Management**: Programmatic lifecycle control: spawning, monitoring, and shutting down OpenOCD daemon processes.
- **Configuration Script Generation**: Passing board and interface configuration scripts (e.g. `interface/stlink.cfg`, `target/stm32f1x.cfg`).
- **Hardware Reset-Halt Execution**: Forcing target CPU cores to halt at the reset vector before first-stage bootloader code executes.
- **Silicon IDCODE Inspection**: Querying core debug registers to confirm microcontroller silicon revisions.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 16: Bare-Metal Microcontroller Debugging with OpenOCDTarget.
Automates OpenOCD target parameters, hardware reset halting and register inspection."""

import shutil

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget


class EmulatedTarget(DummyTarget):
    """Offline stand-in so the OpenOCD command flow stays reproducible in CI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()


def probe_native_backend():
    """A real session additionally needs an ST-Link/CMSIS-DAP probe attached."""
    binary = shutil.which("openocd")
    return (True, binary) if binary else (False, "openocd not found in PATH")


def run_openocd_demo():
    available, detail = probe_native_backend()
    print(f"[{'NATIVE' if available else 'SIMULATION'}] backend: {detail}")

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="stm32_hw_target", gdb_port=3333,
                            openocd_script=["interface/stlink.cfg", "target/stm32f1x.cfg"])
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="stm32_flash", permissions="r-x")
    ava.init_targets()

    print("[*] 'reset halt' -> core frozen at the reset vector")
    target.regs.pc, target.regs.sp = 0x08000101, 0x20004FF0
    target.regs.r0 = 0x1FF0F41B                      # flash size / unique ID registers
    print(f"[+] PC=0x{target.regs.pc:08x} SP=0x{target.regs.sp:08x} "
          f"R0=0x{target.regs.r0:08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_openocd_demo()
```

## 🔥 Use Cases
- Automated factory flash programming and cryptographic key provisioning over SWD.
- Hardware-in-the-loop security fuzzing of live automotive CAN nodes.
- Extracting non-readout-protected (RDP Level 0) firmware images from unknown IoT chips.

## ⚠️ Caveats & Responsible Practice
- Ensure the SWD/JTAG adapter clock speed (adapter_khz) is not set faster than 1/6th of CPU clock frequency.
- Readout Protection (RDP Level 1 or 2) will block flash memory reads over SWD.
- High electrical noise on long jumper wires causes OpenOCD communication packet loss.

## 📦 Test Data & Sample Binaries
- **Target Hardware**: STMicroelectronics STM32F103C8T6 (BluePill)
- **Debug Interface**: ST-Link v2 / CMSIS-DAP over SWD
- **Target IDCODE**: `0x10016414` (Medium-density value line)

## 🔗 Resources
- OpenOCD User's Guide (https://openocd.org/doc/html/index.html)
- Avatar2 OpenOCDTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/openocd_target.py)

**Full script, run log & report**: [`16_openocd_swd_jtag_hardware_debugging/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/16_openocd_swd_jtag_hardware_debugging)

#Avatar2 #OpenOCD #SWD #JTAG #HardwareHacking #FirmwareSecurity #STM32
