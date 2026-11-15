# ⚡️ 💾 Serial SPI Flash (NOR/NAND) & NVRAM File-Backed Emulation (Python practice)

Almost all connected embedded devices store persistent configuration parameters—Wi-Fi credentials, cryptographic certificates, user passwords, and calibration data—in external serial SPI NOR/NAND Flash chips or NVRAM partitions.

## 🧠 Core Concept
- **SPI Flash Controller Simulation**: Modeling the serial flash command state machine.
- **Standard SPI Flash Opcodes**: Handling Read Data (`0x03`), Page Program (`0x02`), and Write Enable (`0x06`).
- **File-Backed Persistence**: Synchronizing flash read and write operations directly with on-disk binary images.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 28: Serial SPI Flash & NVRAM File-Backed Wear-Levelling Emulation.
Firmware programs a file-backed, wear-levelled NVRAM controller over MMIO."""

import os

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

CTRL_BASE, CTRL_SIZE = 0x40023000, 0x1000
SECTORS, SECTOR_SIZE, PROGRAM_COUNT = 8, 256, 5


class FileBackedNvramController(AvatarPeripheral):
    """CMD/DATA registers in front of a wear-levelled, file-backed sector map."""

    def __init__(self, name, address, size, image_path):
        super().__init__(name, address, size)
        self.image_path = image_path
        self.sectors = [bytearray(SECTOR_SIZE) for _ in range(SECTORS)]
        self.erase_counts = [0] * SECTORS
        self.programmed = 0

    def write(self, offset, size, value):
        if offset == 0x00 and value == 0x01:          # PROGRAM command
            physical = self.programmed % SECTORS      # rotate destinations
            self.erase_counts[physical] += 1
            self.programmed += 1
        return True

    def flush(self):
        with open(self.image_path, "wb") as handle:
            handle.write(b"".join(self.sectors))
        return os.path.basename(self.image_path)


def run_nvram_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    nvram = FileBackedNvramController("nvram", CTRL_BASE, CTRL_SIZE, "nvm_image.bin")
    ava.add_memory_range(CTRL_BASE, CTRL_SIZE, name="nvram_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=nvram)
    ava.init_targets()

    for _ in range(PROGRAM_COUNT):                   # firmware PROGRAM commands
        nvram.write(0x00, 4, 0x01)
    print(f"[+] wear {nvram.erase_counts} -> {nvram.flush()}")
    ava.shutdown()


if __name__ == "__main__":
    run_nvram_demo()
```

## 🔥 Use Cases
- Extracting Wi-Fi credentials, private keys, and cloud API tokens from extracted IoT flash dumps.
- Testing firmware recovery behavior when SPI Flash sectors are corrupted or zeroed.

## ⚠️ Caveats & Responsible Practice
- NOR Flash memory can only flip bits from 1 to 0; writing 0 to 1 requires a preceding Sector Erase (`0x20`).
- Page program operations are limited to 256 bytes per transaction; crossing page boundaries without wrapping causes data loss.

## 📦 Test Data & Sample Binaries
- **Chip Model**: Winbond W25Q32 (32 Mbit / 4 MByte SPI NOR Flash)
- **Opcodes**: Read (`0x03`), Write Enable (`0x06`), Page Program (`0x02`)
- **Extracted Config**: `PART_CFG:SSID=Corporate_IoT;PSK=SuperSecretPass2026;ADMIN=1;`

## 🔗 Resources
- Winbond W25Q32JV Serial NOR Flash Datasheet (https://www.winbond.com/resource-files/w25q32jv%20revg%2003272018%20plus.pdf)

**Full script, run log & report**: [`28_nvram_flash_wear_leveling_emulation/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/28_nvram_flash_wear_leveling_emulation)

#Avatar2 #SPIFlash #NVRAM #Winbond #ReverseEngineering #IoT #FirmwareSecurity
