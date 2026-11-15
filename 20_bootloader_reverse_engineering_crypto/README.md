# ⚡️ 🔑 Embedded Bootloader Analysis & Hardware Crypto Key Extraction (Python practice)

Embedded secure bootloaders use hardware cryptographic engines (AES, SHA-256, RSA) to verify and decrypt firmware updates before flashing them into main memory.

## 🧠 Core Concept
- **Hardware Crypto Acceleration**: Offloading AES and SHA operations to memory-mapped cryptographic peripherals.
- **Key Schedule Interception**: Trapping writes to AES Key Registers (`AES_KEYRx`) before cipher rounds begin.
- **Ciphertext Ingestion Tracing**: Monitoring input block transfers (`AES_DINR`) and output plaintext blocks (`AES_DOUTR`).

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 20: Embedded Bootloader Analysis & Hardware Crypto Key Extraction.
Emulates an on-chip AES-256 accelerator to intercept and extract symmetric keys."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

AES_BASE, AES_SIZE, KEY_OFFSET = 0x50060000, 0x1000, 0x10


class STM32AESAccelerator(AvatarPeripheral):
    """Key registers are write-only on silicon - here they are captured word by word."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.key_words = []

    def read(self, offset, size):
        return 1 if offset == 0x04 else 0            # SR: key derivation finished

    def write(self, offset, size, value):
        if KEY_OFFSET <= offset < KEY_OFFSET + 0x20:
            self.key_words.append(value & 0xFFFFFFFF)
        return True

    def extract_full_256bit_key(self):
        return b"".join(word.to_bytes(4, "little") for word in self.key_words)


def run_crypto_extraction_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="bootloader_cpu")
    target.update_state(TargetStates.STOPPED)
    aes = STM32AESAccelerator("stm32_aes", AES_BASE, AES_SIZE)
    route = ava.add_memory_range(AES_BASE, AES_SIZE, name="aes_mmio",
                                 permissions="rw-", forwarded=True, forwarded_to=aes)
    ava.init_targets()

    for index, word in enumerate([0x03020100, 0x07060504, 0x0B0A0908, 0x0F0E0D0C,
                                  0x13121110, 0x17161514, 0x1B1A1918, 0x1F1E1D1C]):
        route.forwarded_to.write(KEY_OFFSET + index * 4, 4, word)   # bootloader writes
    key = aes.extract_full_256bit_key()
    print(f"[+] AES-256 key ({len(key)} B): {key.hex().upper()}")
    ava.shutdown()


if __name__ == "__main__":
    run_crypto_extraction_demo()
```

## 🔥 Use Cases
- Extracting firmware decryption keys from encrypted OTA (Over-The-Air) update bootloaders.
- Recovering proprietary AES authentication keys from automotive smart keys and immobilizers.
- Decrypting proprietary smart home IoT device flash contents extracted via SPI dumps.

## ⚠️ Caveats & Responsible Practice
- Hardware accelerators on high-security chips (e.g. NXP EdgeLock, STM32 TrustZone) use write-only key slots.
- If keys are derived dynamically via PBKDF2 or HKDF, capture the derivation salt and iteration count.

## 📦 Test Data & Sample Binaries
- **Cryptographic Accelerator**: STM32 Hardware AES Engine (`AES_KEYR0`-`AES_KEYR7`)
- **Base Address**: `0x50060000` (Size: 4 KB)
- **Extracted Key**: `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f` (256 bits)

## 🔗 Resources
- STM32 Cryptographic Processor (CRYP/AES) Reference Manual (https://www.st.com/resource/en/application_note/an3969-stm32-crossseries-cryptographic-library-stmicroelectronics.pdf)

**Full script, run log & report**: [`20_bootloader_reverse_engineering_crypto/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/20_bootloader_reverse_engineering_crypto)

#Avatar2 #Cryptography #AES256 #KeyExtraction #Bootloader #ReverseEngineering #FirmwareSecurity
