# ⚡️ 🛰 Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines) with Avatar2 Framework (Python practice)

IoT devices, medical monitors, and industrial controllers rely on serial communication buses (I2C and SPI) to query environmental sensors: temperature probes, 3-axis accelerometers, gyroscopes, and Real-Time Clocks (RTC). When firmware initializes, it performs handshake queries—such as checking the sensor's `WHO_AM_I` identification register—and halts if the sensor does not acknowledge. By implementing a virtual sensor peripheral in Avatar2, security researchers can emulate the complete SPI/I2C register bank, respond to device inquiries, and feed synthetic accelerometer or temperature data streams directly into the running firmware.

## 🧠 Core Concept
- **SPI & I2C Bus Abstraction**: Modeling multi-drop serial buses with slave address decoding.
- `WHO_AM_I` Device Identification: Returning hardware sensor IDs (e.g. `0x33` for LIS3DH accelerometer).
- **Register Address Pointer State Machine**: Tracking internal register offset pointers across multi-byte transactions.
- **Synthetic Sensor Data Generation**: Generating structured 16-bit 2's-complement X/Y/Z accelerometer data.
- **Sensor Fuzzing**: Injecting impossible acceleration or temperature values to evaluate firmware validation routines.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 27: Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines)
Real firmware talks to a modeled I2C temperature sensor and an SPI NOR flash over MMIO.
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
I2C_BASE = 0x40005400
I2C_SIZE = 0x1000
SPI_BASE = 0x40003800
SPI_SIZE = 0x1000

I2C_CMD_READ_TEMP = 0xA1
SENSOR_TEMPERATURE = 0x1A          # 26 C
SPI_CMD_JEDEC_ID = 0x9F
SPI_JEDEC_ID = 0xEF4017            # Winbond W25Q64

REG_IDS = {
    "r0": uc_arm.UC_ARM_REG_R0, "r1": uc_arm.UC_ARM_REG_R1, "r2": uc_arm.UC_ARM_REG_R2,
    "r3": uc_arm.UC_ARM_REG_R3, "r4": uc_arm.UC_ARM_REG_R4, "r5": uc_arm.UC_ARM_REG_R5,
    "r6": uc_arm.UC_ARM_REG_R6, "r7": uc_arm.UC_ARM_REG_R7,
}


class MmioBridge:
    """Dispatches guest MMIO writes/reads to an AvatarPeripheral (reads patch the target register)."""

    def __init__(self, uc, peripheral, base, size, label):
        self.peripheral = peripheral
        self.label = label
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


class VirtualI2CBus(AvatarPeripheral):
    """I2C master controller + temperature sensor slave.
      0x00: CR1   [bit 0: enable, bit 8: start]
      0x04: DR    [write: command byte / read: response byte]
      0x08: SR    [bit 1: RXNE, bit 2: BUSY]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cr1
        self.write_handler[0x04:0x08] = self.write_dr
        self.read_handler[0x04:0x08] = self.read_dr
        self.read_handler[0x08:0x0C] = self.read_sr
        self.enabled = False
        self.response = 0
        self.frames = []

    def write_cr1(self, offset, size, value, pc=0):
        self.enabled = bool(value & 1)
        print(f"[I2C] CR1 <- 0x{value:08x} (enabled={self.enabled}, PC=0x{pc:08x})")
        return True

    def write_dr(self, offset, size, value, pc=0):
        command = value & 0xFF
        if command == I2C_CMD_READ_TEMP:
            self.response = SENSOR_TEMPERATURE
            self.frames.append(("READ_TEMP", self.response))
            print(f"[I2C] Command 0x{command:02x} -> sensor returns {self.response} C")
        else:
            self.response = 0xFF
            self.frames.append(("NACK", 0xFF))
            print(f"[I2C] Command 0x{command:02x} -> NACK from slave")
        return True

    def read_dr(self, offset, size, pc=0):
        print(f"[I2C] DR read by firmware: 0x{self.response:02x}")
        return self.response

    def read_sr(self, offset, size, pc=0):
        return 0x02 if self.enabled else 0x00


class VirtualSpiFlash(AvatarPeripheral):
    """SPI master + NOR flash slave (JEDEC identification only).
      0x00: CR1   [bit 0: enable]
      0x04: DR    [write: command / read: response]
      0x08: SR    [bit 1: ready]
    """

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.write_handler[0x00:0x04] = self.write_cr1
        self.write_handler[0x04:0x08] = self.write_dr
        self.read_handler[0x04:0x08] = self.read_dr
        self.enabled = False
        self.response = 0
        self.frames = []

    def write_cr1(self, offset, size, value, pc=0):
        self.enabled = bool(value & 1)
        print(f"[SPI] CR1 <- 0x{value:08x} (enabled={self.enabled}, PC=0x{pc:08x})")
        return True

    def write_dr(self, offset, size, value, pc=0):
        command = value & 0xFF
        if command == SPI_CMD_JEDEC_ID:
            self.response = SPI_JEDEC_ID
            self.frames.append(("JEDEC_ID", self.response))
            print(f"[SPI] Command 0x{command:02x} -> JEDEC ID 0x{self.response:06x}")
        else:
            self.response = 0x00
            self.frames.append(("UNKNOWN", 0))
            print(f"[SPI] Command 0x{command:02x} -> ignored")
        return True

    def read_dr(self, offset, size, pc=0):
        print(f"[SPI] DR read by firmware: 0x{self.response:06x}")
        return self.response


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x40005400      @ I2C controller
        movs r0, #1
        str  r0, [r4, #0x00]      @ enable the bus
        movs r0, #0xA1
        str  r0, [r4, #0x04]      @ request the temperature
        ldr  r1, [r4, #0x08]      @ poll the status register
        ldr  r2, [r4, #0x04]      @ read the sensor response
        ldr  r5, =0x20000000
        str  r2, [r5]             @ stash temperature in RAM

        ldr  r6, =0x40003800      @ SPI controller
        movs r0, #1
        str  r0, [r6, #0x00]      @ enable the bus
        movs r0, #0x9F
        str  r0, [r6, #0x04]      @ request the JEDEC ID
        ldr  r3, [r6, #0x04]      @ read the flash response
        str  r3, [r5, #4]         @ stash the ID in RAM
        b    .
        """
    )
    return bytes(code)


def run_sensor_bus_demo() -> None:
    print("[*] Initializing Multi-Drop Sensor Bus Simulation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_sensor_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")

        i2c = VirtualI2CBus("i2c1", I2C_BASE, I2C_SIZE)
        spi = VirtualSpiFlash("spi1", SPI_BASE, SPI_SIZE)
        ava.add_memory_range(I2C_BASE, I2C_SIZE, name="i2c_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=i2c)
        ava.add_memory_range(SPI_BASE, SPI_SIZE, name="spi_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=spi)
        ava.init_targets()
        print(f"[+] I2C bus at 0x{I2C_BASE:08x}, SPI bus at 0x{SPI_BASE:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(I2C_BASE, I2C_SIZE)
        uc.mem_map(SPI_BASE, SPI_SIZE)
        uc.mem_write(FLASH_BASE, assemble_firmware())
        i2c_bridge = MmioBridge(uc, i2c, I2C_BASE, I2C_SIZE, "i2c")
        spi_bridge = MmioBridge(uc, spi, SPI_BASE, SPI_SIZE, "spi")
        uc.reg_write(uc_arm.UC_ARM_REG_SP, RAM_BASE + MEM_SIZE)

        print("[*] Executing firmware that probes both sensor buses...")
        uc.emu_start(FLASH_BASE | 1, 0, count=400)

        temperature = uc.reg_read(uc_arm.UC_ARM_REG_R2)
        jedec = uc.reg_read(uc_arm.UC_ARM_REG_R3)
        ram_temp = int.from_bytes(bytes(uc.mem_read(RAM_BASE, 4)), "little")
        ram_id = int.from_bytes(bytes(uc.mem_read(RAM_BASE + 4, 4)), "little")

        print(f"[+] I2C frames : {i2c.frames}")
        print(f"[+] SPI frames : {spi.frames}")
        print(f"[+] Temperature: {temperature} C (RAM copy: {ram_temp})")
        print(f"[+] Flash ID   : 0x{jedec:06x} (RAM copy: 0x{ram_id:06x})")
        print(f"[+] MMIO traffic: I2C {len(i2c_bridge.writes)}w/{len(i2c_bridge.reads)}r, "
              f"SPI {len(spi_bridge.writes)}w/{len(spi_bridge.reads)}r")

        assert temperature == SENSOR_TEMPERATURE == ram_temp
        assert jedec == SPI_JEDEC_ID == ram_id
        assert ("READ_TEMP", SENSOR_TEMPERATURE) in i2c.frames
        assert ("JEDEC_ID", SPI_JEDEC_ID) in spi.frames

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] I2C/SPI sensor bus simulation verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_sensor_bus_demo()
```

## 🔥 Use Cases
- Fuzzing medical infusion pump firmware with out-of-range sensor readings.
- Simulating drone IMU accelerometer and gyroscope data during navigation algorithm testing.
- Analyzing automotive tire pressure monitoring system (TPMS) RF sensor decoders.
- Bypassing hardware tamper detection sensors that measure physical enclosure tilt.
- Testing battery management system (BMS) response to simulated over-temperature alarms.

## ⚠️ Caveats & Responsible Practice
- Real I2C peripherals use 7-bit addressing; ensure your model correctly handles the R/W direction bit (bit 0).
- Many sensors require sequential multi-byte reads using auto-increment register address flags (e.g. MSB set in address).
- Pay close attention to endianness: accelerometer 16-bit readings are typically little-endian.
- Missing pull-up resistors in real circuits cause bus floating; simulate bus NACK responses when testing error paths.
- Both bus engines are driven by real executed code; slave responses come from the Python models, which is exactly how peripheral emulation is layered in production fuzzing rigs.

## 📦 Test Data & Sample Binaries / Targets
- **Sensor Device**: STMicroelectronics LIS3DH MEMS Accelerometer
- **Device ID (`WHO_AM_I`)**: `0x33`
- **Simulated Gravity Vector**: `X = 0.0G`, `Y = 0.0G`, `Z = +1.0G` (`0x4000`)

## 🔗 Resources
- ST LIS3DH 3-Axis Accelerometer Datasheet (https://www.st.com/resource/en/datasheet/lis3dh.pdf)
- I2C and SPI Bus Protocol Principles (https://www.analog.com/en/analog-dialogue/articles/i2c-primer.html)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #I2C #SPI #Sensors #LIS3DH #HardwareEmulation #FirmwareSecurity
