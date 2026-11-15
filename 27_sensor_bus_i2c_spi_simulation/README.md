# ⚡️ 🛰 Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines) with Avatar2 Framework (Python practice)
_Post 27/30 · Avatar2 firmware orchestration playbook_

IoT devices, medical monitors, and industrial controllers rely on serial communication buses (I2C and SPI) to query environmental sensors: temperature probes, 3-axis accelerometers, gyroscopes, and Real-Time Clocks (RTC). When firmware initializes, it performs handshake queries—such as checking the sensor's `WHO_AM_I` identification register—and halts if the sensor does not acknowledge.

## 🧠 Core Concept
- **SPI & I2C Bus Abstraction**: Modeling multi-drop serial buses with slave address decoding.
- `WHO_AM_I` Device Identification: Returning hardware sensor IDs (e.g. `0x33` for LIS3DH accelerometer).
- **Register Address Pointer State Machine**: Tracking internal register offset pointers across multi-byte transactions.
- **Synthetic Sensor Data Generation**: Generating structured 16-bit 2's-complement X/Y/Z accelerometer data.
- **Sensor Fuzzing**: Injecting impossible acceleration or temperature values to evaluate firmware validation routines.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
i2c = VirtualI2CBus("i2c1", I2C_BASE, I2C_SIZE)
spi = VirtualSpiFlash("spi1", SPI_BASE, SPI_SIZE)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
```

## 🔥 Use Cases
- Fuzzing medical infusion pump firmware with out-of-range sensor readings.
- Simulating drone IMU accelerometer and gyroscope data during navigation algorithm testing.
- Analyzing automotive tire pressure monitoring system (TPMS) RF sensor decoders.
- Bypassing hardware tamper detection sensors that measure physical enclosure tilt.
- Testing battery management system (BMS) response to simulated over-temperature alarms.

## ⚠️ Caveats
- Real I2C peripherals use 7-bit addressing; ensure your model correctly handles the R/W direction bit (bit 0).
- Many sensors require sequential multi-byte reads using auto-increment register address flags (e.g. MSB set in address).
- Pay close attention to endianness: accelerometer 16-bit readings are typically little-endian.
- Missing pull-up resistors in real circuits cause bus floating; simulate bus NACK responses when testing error paths.

## 📦 Target
- **Sensor Device**: STMicroelectronics LIS3DH MEMS Accelerometer
- **Device ID (`WHO_AM_I`)**: `0x33`
- **Simulated Gravity Vector**: `X = 0.0G`, `Y = 0.0G`, `Z = +1.0G` (`0x4000`)

## 🔗 Resources
- ST LIS3DH 3-Axis Accelerometer Datasheet (https://www.st.com/resource/en/datasheet/lis3dh.pdf)
- I2C and SPI Bus Protocol Principles (https://www.analog.com/en/analog-dialogue/articles/i2c-primer.html)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

**Runnable source, run log & report**: [`27_sensor_bus_i2c_spi_simulation`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/27_sensor_bus_i2c_spi_simulation)

#Avatar2 #I2C #SPI #Sensors #LIS3DH #HardwareEmulation #FirmwareSecurity
