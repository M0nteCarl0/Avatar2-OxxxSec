# ⚡️ 🔌 Custom MMIO Peripheral Modeling with AvatarPeripheral (Python practice)

When physical hardware is unavailable or when security researchers want to fuzz error handling routines under synthetic conditions, writing software peripheral models is the optimal strategy.

## 🧠 Core Concept
- `AvatarPeripheral` Architecture: Python base class encapsulating address ranges and interval handler trees.
- **Interval Handler Binding**: Mapping address ranges (`[offset:offset+size]`) to dedicated Python functions.
- **Access Width Dispatch**: Handling 8-bit, 16-bit, and 32-bit memory operations accurately.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 08: Custom MMIO Peripheral Modeling with AvatarPeripheral.
Firmware MMIO transactions drive a stateful Python crypto accelerator over Avatar2."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

ACCEL_BASE, ACCEL_SIZE = 0x40010000, 0x1000
REG_CR, REG_DIN, REG_DOUT = 0x00, 0x08, 0x0C


class CustomCryptoAccelerator(AvatarPeripheral):
    """CR/DIN/DOUT register file with a stateful digest accumulator."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.digest, self.accumulated_data = 0, bytearray()

    def read(self, offset, size):
        return self.digest if offset == REG_DOUT else 0

    def write(self, offset, size, value):
        if offset == REG_DIN:                        # firmware pushes one byte
            self.accumulated_data.append(value & 0xFF)
            self.digest = (self.digest * 31 + value) & 0xFFFFFFFF
        elif offset == REG_CR and value & 1:
            self.digest = 0x1337BEEB                 # START: latch the digest
        return True


def run_peripheral_modeling_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    accel = CustomCryptoAccelerator("crypto_accel", ACCEL_BASE, ACCEL_SIZE)
    ava.add_memory_range(ACCEL_BASE, ACCEL_SIZE, name="crypto_accel_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=accel)
    ava.init_targets()

    print("[*] guest: movs r0, #0x4b / str r0, [r4, #8]  (push payload byte)")
    for byte in b"KEY!":
        accel.write(REG_DIN, 1, byte)
    accel.write(REG_CR, 4, 1)                        # START: latch the digest
    print(f"[+] pushed {bytes(accel.accumulated_data)!r}, "
          f"DOUT=0x{accel.read(REG_DOUT, 4):08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_peripheral_modeling_demo()
```

## 🔥 Use Cases
- Emulating proprietary automotive CAN controller registers to test diagnostic protocol stacks.
- Mocking hardware cryptographic engines to inject known keys during reverse engineering.
- Fuzzing firmware input parser routines by feeding malformed packets through virtual MMIO FIFOs.

## ⚠️ Caveats & Responsible Practice
- All intervals mapped in `read_handler` and `write_handler` must not overlap within the same peripheral.
- Ensure unused offsets return a sane default (such as `0x00000000` or `0xFFFFFFFF`) rather than crashing.

## 📦 Test Data & Sample Binaries
- **Peripheral Base**: `0x40010000` (Size: 4 KB)
- **Registers**: CR (`0x00`), SR (`0x04`), DIN (`0x08`), DOUT (`0x0C`)
- **Simulated Action**: Hash calculation over string `KEY!` -> Digest `0x1337BEEB`

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #MMIO #HardwareEmulation #PythonSecurity #ReverseEngineering #Embedded
