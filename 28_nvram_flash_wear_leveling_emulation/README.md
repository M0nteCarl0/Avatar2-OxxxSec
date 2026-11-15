# ⚡️ 💾 Serial SPI Flash (NOR/NAND) & NVRAM File-Backed Emulation with Avatar2 Framework (Python practice)
_Post 28/30 · Avatar2 firmware orchestration playbook_

Almost all connected embedded devices store persistent configuration parameters—Wi-Fi credentials, cryptographic certificates, user passwords, and calibration data—in external serial SPI NOR/NAND Flash chips or NVRAM partitions. Firmware interacts with flash memory using standardized command opcodes (Read `0x03`, Write Enable `0x06`, Sector Erase `0x20`, Page Program `0x02`).

## 🧠 Core Concept
- **SPI Flash Controller Simulation**: Modeling the serial flash command state machine.
- **Standard SPI Flash Opcodes**: Handling Read Data (`0x03`), Page Program (`0x02`), and Write Enable (`0x06`).
- **File-Backed Persistence**: Synchronizing flash read and write operations directly with on-disk binary images.
- **NVRAM Partition Table Parsing**: Extracting structured parameter blocks (keys, SSID, hashed credentials).
- **Credential Mutation**: Injecting modified configuration payloads to evaluate access control bypasses.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
nvram = FileBackedNvramController("nvram", CTRL_BASE, CTRL_SIZE, image_path)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
```

## 🔥 Use Cases
- Extracting Wi-Fi credentials, private keys, and cloud API tokens from extracted IoT flash dumps.
- Testing firmware recovery behavior when SPI Flash sectors are corrupted or zeroed.
- Analyzing embedded flash file systems (LittleFS, SPIFFS, UBIFS) for directory traversal flaws.
- Bypassing device authentication by hot-patching user credentials inside persistent NVRAM blocks.
- Evaluating flash wear-leveling algorithms under accelerated write-cycle stress tests.

## ⚠️ Caveats
- NOR Flash memory can only flip bits from 1 to 0; writing 0 to 1 requires a preceding Sector Erase (`0x20`).
- Page program operations are limited to 256 bytes per transaction; crossing page boundaries without wrapping causes data loss.
- Ensure the backing flash file is opened in binary mode (`rb+`) to avoid line-ending translation issues on Windows.
- Simulating slow sector erase delays (~50ms) is essential if firmware tests erase completion status bits.

## 📦 Target
- **Chip Model**: Winbond W25Q32 (32 Mbit / 4 MByte SPI NOR Flash)
- **Opcodes**: Read (`0x03`), Write Enable (`0x06`), Page Program (`0x02`)
- **Extracted Config**: `PART_CFG:SSID=Corporate_IoT;PSK=SuperSecretPass2026;ADMIN=1;`

## 🔗 Resources
- Winbond W25Q32JV Serial NOR Flash Datasheet (https://www.winbond.com/resource-files/w25q32jv%20revg%2003272018%20plus.pdf)
- Embedded Flash File Systems: LittleFS Architecture (https://github.com/littlefs-project/littlefs)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

**Runnable source, run log & report**: [`28_nvram_flash_wear_leveling_emulation`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/28_nvram_flash_wear_leveling_emulation)

#Avatar2 #SPIFlash #NVRAM #Winbond #ReverseEngineering #IoT #FirmwareSecurity
