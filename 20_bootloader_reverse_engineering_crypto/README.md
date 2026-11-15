# ⚡️ 🔑 Embedded Bootloader Analysis & Hardware Crypto Key Extraction with Avatar2 Framework (Python practice)
_Post 20/30 · Avatar2 firmware orchestration playbook_

Embedded secure bootloaders use hardware cryptographic engines (AES, SHA-256, RSA) to verify and decrypt firmware updates before flashing them into main memory. Attempting to reverse engineer these cryptographic routines purely via static disassembly is challenging because the key scheduling and round transformations take place entirely inside silicon MMIO registers.

## 🧠 Core Concept
- **Hardware Crypto Acceleration**: Offloading AES and SHA operations to memory-mapped cryptographic peripherals.
- **Key Schedule Interception**: Trapping writes to AES Key Registers (`AES_KEYRx`) before cipher rounds begin.
- **Ciphertext Ingestion Tracing**: Monitoring input block transfers (`AES_DINR`) and output plaintext blocks (`AES_DOUTR`).
- **Firmware Decryption Loop Recovery**: Recovering decrypted stage-2 payload binaries directly from memory.
- **Static vs Dynamic Synergies**: Combining static Ghidra disassembly with live dynamic key extraction.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="bootloader_cpu")
target.update_state(TargetStates.STOPPED)
aes_engine = STM32AESAccelerator("stm32_aes", 0x50060000, 0x1000)
ava.init_targets()
reg_offset = 0x50060010 + (i * 4)
mr.forwarded_to.write_memory(reg_offset, 4, word, pc=0x08000340)
recovered_key = aes_engine.extract_full_256bit_key()
ava.stop()
ava.fast_queue_listener.stop()
```

## 🔥 Use Cases
- Extracting firmware decryption keys from encrypted OTA (Over-The-Air) update bootloaders.
- Recovering proprietary AES authentication keys from automotive smart keys and immobilizers.
- Decrypting proprietary smart home IoT device flash contents extracted via SPI dumps.
- Validating that cryptographic keys are not stored in plaintext inside internal bootloader ROM.
- Auditing secure boot implementations against side-channel key leakage.

## ⚠️ Caveats
- Hardware accelerators on high-security chips (e.g. NXP EdgeLock, STM32 TrustZone) use write-only key slots.
- If keys are derived dynamically via PBKDF2 or HKDF, capture the derivation salt and iteration count.
- Be mindful of word endianness when assembling 32-bit register writes into contiguous byte keys.
- Secure bootloaders often clear key registers immediately after decryption to thwart RAM dumping.

## 📦 Target
- **Cryptographic Accelerator**: STM32 Hardware AES Engine (`AES_KEYR0`-`AES_KEYR7`)
- **Base Address**: `0x50060000` (Size: 4 KB)
- **Extracted Key**: `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f` (256 bits)

## 🔗 Resources
- STM32 Cryptographic Processor (CRYP/AES) Reference Manual (https://www.st.com/resource/en/application_note/an3969-stm32-crossseries-cryptographic-library-stmicroelectronics.pdf)
- Reverse Engineering Embedded Cryptographic Algorithms (https://eprint.iacr.org/2019/358.pdf)
- Avatar2 Peripheral Modeling Architecture (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

**Runnable source, run log & report**: [`20_bootloader_reverse_engineering_crypto`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/20_bootloader_reverse_engineering_crypto)

#Avatar2 #Cryptography #AES256 #KeyExtraction #Bootloader #ReverseEngineering #FirmwareSecurity
