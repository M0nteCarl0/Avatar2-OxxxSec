#!/usr/bin/env python3
"""
Post 20: Embedded Bootloader Analysis & Hardware Crypto Key Extraction
Emulating an on-chip AES-256 accelerator peripheral to intercept and extract symmetric decryption keys.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

class STM32AESAccelerator(AvatarPeripheral):
    """
    Simulates STM32 AES Hardware Cryptographic Accelerator.
    Registers:
      0x00: Control Register (AES_CR)
      0x04: Status Register (AES_SR)
      0x08: Data Input Register (AES_DINR)
      0x0C: Data Output Register (AES_DOUTR)
      0x10-0x2C: Key Registers (AES_KEYR0 - AES_KEYR7 for 256-bit key)
    """
    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x04:0x08] = self.read_sr
        self.write_handler[0x10:0x30] = self.write_key_register
        self.write_handler[0x08:0x0C] = self.write_dinr
        
        self.key_words = [0] * 8
        self.recovered_key_bytes = bytearray()
        self.sr = 0x01  # CCF: Computation Complete Flag ready

    def read_sr(self, offset, size, pc=0):
        return self.sr

    def write_key_register(self, offset, size, value, pc=0):
        reg_index = (offset - 0x10) // 4
        self.key_words[reg_index] = value
        print(f"[AES KEY WRITE] Offset: 0x{offset:02x} (KEYR{reg_index}) = 0x{value:08x} (From PC: 0x{pc:08x})")
        return True

    def write_dinr(self, offset, size, value, pc=0):
        print(f"[AES CIPHERTEXT] Pushed block word: 0x{value:08x}")
        return True

    def extract_full_256bit_key(self) -> bytes:
        # Reconstruct key from 8 32-bit little-endian words
        full_key = bytearray()
        for word in self.key_words:
            full_key.extend(word.to_bytes(4, "little"))
        return bytes(full_key)

def run_crypto_extraction_demo() -> None:
    print("[*] Initializing Bootloader Hardware Crypto Interception...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_crypto_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="bootloader_cpu")
        target.update_state(TargetStates.STOPPED)
        
        # Map AES hardware accelerator at 0x50060000
        aes_engine = STM32AESAccelerator("stm32_aes", 0x50060000, 0x1000)
        mr = ava.add_memory_range(
            0x50060000, 0x1000,
            name="aes_mmio",
            permissions="rw-",
            forwarded=True,
            forwarded_to=aes_engine
        )
        
        ava.init_targets()
        print(f"[+] Hardware AES Accelerator mapped at 0x50060000.")
        
        # Simulate bootloader programming the 256-bit AES key:
        # Key: 0x000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F
        simulated_key_words = [
            0x03020100, 0x07060504, 0x0B0A0908, 0x0F0E0D0C,
            0x13121110, 0x17161514, 0x1B1A1918, 0x1F1E1D1C
        ]
        
        print("[*] Simulating bootloader programming AES-256 Key Registers...")
        for i, word in enumerate(simulated_key_words):
            reg_offset = 0x50060010 + (i * 4)
            mr.forwarded_to.write_memory(reg_offset, 4, word, pc=0x08000340)
            
        # Extract the reconstructed key
        recovered_key = aes_engine.extract_full_256bit_key()
        print()
        print("=" * 65)
        print("  CRACKED AES-256 FIRMWARE ENCRYPTION KEY")
        print("=" * 65)
        print(f"Hex String : {recovered_key.hex().upper()}")
        print(f"Key Length : {len(recovered_key) * 8} bits ({len(recovered_key)} bytes)")
        print("=" * 65)
        
        assert len(recovered_key) == 32
        assert recovered_key.hex() == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
        print("[+] Key integrity verification: 100% MATCH with expected bootloader key!")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hardware cryptographic key extraction verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_crypto_extraction_demo()
