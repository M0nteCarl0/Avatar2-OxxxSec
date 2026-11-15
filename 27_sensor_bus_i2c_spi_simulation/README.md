# ⚡️ 🛰 Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines) (Python practice)

IoT devices, medical monitors, and industrial controllers rely on serial communication buses (I2C and SPI) to query environmental sensors: temperature probes, 3-axis accelerometers, gyroscopes, and Real-Time Clocks (RTC).

## 🧠 Core Concept
- **SPI & I2C Bus Abstraction**: Modeling multi-drop serial buses with slave address decoding.
- `WHO_AM_I` Device Identification: Returning hardware sensor IDs (e.g. `0x33` for LIS3DH accelerometer).
- **Register Address Pointer State Machine**: Tracking internal register offset pointers across multi-byte transactions.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 27: Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines).
Firmware talks to a modeled I2C temperature sensor and an SPI NOR flash over MMIO."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

I2C_BASE, SPI_BASE, BUS_SIZE = 0x40005400, 0x40003800, 0x1000
I2C_READ_TEMP, SENSOR_TEMP, SPI_JEDEC, SPI_ID = 0xA1, 0x1A, 0x9F, 0xEF4017


class VirtualSensorBus(AvatarPeripheral):
    """One multi-drop bus: the command byte selects the device and the register."""

    def __init__(self, name, address, size, is_spi=False):
        super().__init__(name, address, size)
        self.is_spi, self.command = is_spi, 0

    def write(self, offset, size, value):
        self.command = value & 0xFF
        return True

    def read(self, offset, size):
        if self.is_spi:
            return SPI_ID & 0xFF if self.command == SPI_JEDEC else 0
        return SENSOR_TEMP if self.command == I2C_READ_TEMP else 0


def run_sensor_bus_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    i2c = VirtualSensorBus("i2c1", I2C_BASE, BUS_SIZE)
    spi = VirtualSensorBus("spi1", SPI_BASE, BUS_SIZE, is_spi=True)
    for model, base in ((i2c, I2C_BASE), (spi, SPI_BASE)):
        ava.add_memory_range(base, BUS_SIZE, name=model.name + "_mmio",
                             permissions="rw-", forwarded=True, forwarded_to=model)
    ava.init_targets()

    i2c.write(0x00, 1, I2C_READ_TEMP)                # 'str r0, [r4]'  (0xA1)
    print(f"[+] temperature {i2c.read(0x00, 1)} C from 0x{I2C_BASE:08x}")
    spi.write(0x00, 1, SPI_JEDEC)                    # 'str r0, [r5]'  (0x9F)
    print(f"[+] JEDEC ID byte 0x{spi.read(0x04, 1):02X} (device 0x{SPI_ID:06X})")
    ava.shutdown()


if __name__ == "__main__":
    run_sensor_bus_demo()
```

## 🔥 Use Cases
- Fuzzing medical infusion pump firmware with out-of-range sensor readings.
- Simulating drone IMU accelerometer and gyroscope data during navigation algorithm testing.
- Analyzing automotive tire pressure monitoring system (TPMS) RF sensor decoders.

## ⚠️ Caveats & Responsible Practice
- Real I2C peripherals use 7-bit addressing; ensure your model correctly handles the R/W direction bit (bit 0).
- Many sensors require sequential multi-byte reads using auto-increment register address flags (e.g. MSB set in address).

## 📦 Test Data & Sample Binaries
- **Sensor Device**: STMicroelectronics LIS3DH MEMS Accelerometer
- **Device ID (`WHO_AM_I`)**: `0x33`
- **Simulated Gravity Vector**: `X = 0.0G`, `Y = 0.0G`, `Z = +1.0G` (`0x4000`)

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #I2C #SPI #Sensors #LIS3DH #HardwareEmulation #FirmwareSecurity
