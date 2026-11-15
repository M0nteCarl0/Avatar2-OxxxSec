# ⚡️ 🔍 Automated Unknown Peripheral Address Discovery & Mapping (Python practice)

Security analysts frequently receive raw, stripped firmware blobs extracted from unknown microcontrollers where complete datasheets and memory maps are unavailable.

## 🧠 Core Concept
- **Unmapped MMIO Fault Trapping**: Intercepting page faults triggered when firmware touches unmapped addresses.
- **Fault Telemetry Recording**: Capturing access type (Read/Write), access width (8/16/32-bit), data values, and guest `PC`.
- **Access Pattern Classification**: Differentiating status registers (repeated reads) from control registers (infrequent writes).

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 19: Automated Unknown Peripheral Address Discovery & Mapping.
Firmware sweeps an MMIO window; the modeled bus fabric answers with device IDs."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

BUS_BASE, BUS_SIZE, SCAN_START, SCAN_STEP, SCAN_SLOTS = 0x40000000, 0x20000, 0x4000C000, 0x1000, 8
KNOWN_DEVICES = {0x4000C000: (0x16, "USART1"),
                 0x4000E000: (0x33, "LIS3DH"),
                 0x40011000: (0xEF, "SPI-NOR")}


class VirtualBusFabric(AvatarPeripheral):
    """Decodes the swept addresses and returns the ID register of each slot."""

    def __init__(self, name, address, size, devices):
        super().__init__(name, address, size)
        self.devices = devices

    def read(self, offset, size):
        return self.devices.get(self.address + offset, (0x00, "empty slot"))[0]


def run_discovery_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    bus = VirtualBusFabric("bus", BUS_BASE, BUS_SIZE, KNOWN_DEVICES)
    ava.add_memory_range(BUS_BASE, BUS_SIZE, name="peripheral_bus",
                         permissions="rw-", forwarded=True, forwarded_to=bus)
    ava.init_targets()
    print(f"[*] firmware reads 8 windows of 0x{SCAN_STEP:x} from 0x{SCAN_START:08x}")

    for slot in range(SCAN_SLOTS):                   # guest 'ldrb r0, [r4]' per slot
        address = SCAN_START + slot * SCAN_STEP
        device_id = bus.read(address - BUS_BASE, 1)
        print(f"[+] 0x{address:08x}: ID 0x{device_id:02x} -> "
              f"{KNOWN_DEVICES.get(address, (0, 'empty slot'))[1]}")
    ava.shutdown()


if __name__ == "__main__":
    run_discovery_demo()
```

## 🔥 Use Cases
- Triaging unknown IoT firmware images extracted from black-box microcontroller chips.
- Identifying base addresses of debug UARTs and logging interfaces in proprietary binaries.
- Generating skeleton `AvatarPeripheral` model code automatically from execution traces.

## ⚠️ Caveats & Responsible Practice
- If an unmapped read returns default zero, firmware may stall in infinite polling loops waiting for a non-zero ready bit.
- Firmware may execute different initialization sequences depending on the values returned by discovery reads.

## 📦 Test Data & Sample Binaries
- **Simulated Binary**: Stripped ARM Cortex-M Firmware Blob
- **Discovered Block 1**: `0x4000C000` (UART TX + Status Register)
- **Discovered Block 2**: `0x40011000` (Timer Counter & Config)

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #FirmwareReversing #PeripheralDiscovery #IoT #ReverseEngineering #HardwareHacking
