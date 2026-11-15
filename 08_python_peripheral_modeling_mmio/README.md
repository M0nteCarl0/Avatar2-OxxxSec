# ⚡️ 🔌 Custom MMIO Peripheral Modeling with AvatarPeripheral with Avatar2 Framework (Python practice)
_Post 08/30 · Avatar2 firmware orchestration playbook_

When physical hardware is unavailable or when security researchers want to fuzz error handling routines under synthetic conditions, writing software peripheral models is the optimal strategy. Avatar2 provides the `AvatarPeripheral` base class, allowing researchers to model hardware devices entirely in Python.

## 🧠 Core Concept
- `AvatarPeripheral` Architecture: Python base class encapsulating address ranges and interval handler trees.
- **Interval Handler Binding**: Mapping address ranges (`[offset:offset+size]`) to dedicated Python functions.
- **Access Width Dispatch**: Handling 8-bit, 16-bit, and 32-bit memory operations accurately.
- **Program Counter Awareness**: Inspecting the guest `pc` parameter to determine which firmware function accessed the peripheral.
- **Stateful Register Latching**: Simulating read-clear, write-1-to-clear, and auto-incrementing hardware behaviors.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
accelerator = CustomCryptoAccelerator("crypto_accel", ACCEL_BASE, ACCEL_SIZE)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
uc.mem_map(ACCEL_BASE, ACCEL_SIZE)
uc.mem_write(FLASH_BASE, assemble_firmware())
```

## 🔥 Use Cases
- Emulating proprietary automotive CAN controller registers to test diagnostic protocol stacks.
- Mocking hardware cryptographic engines to inject known keys during reverse engineering.
- Fuzzing firmware input parser routines by feeding malformed packets through virtual MMIO FIFOs.
- Simulating sensor failures and hardware fault conditions to evaluate safety mechanisms.
- Accelerating software-in-the-loop (SIL) development before hardware tape-out.

## ⚠️ Caveats
- All intervals mapped in `read_handler` and `write_handler` must not overlap within the same peripheral.
- Ensure unused offsets return a sane default (such as `0x00000000` or `0xFFFFFFFF`) rather than crashing.
- Be mindful of endianness when handling sub-word (8-bit or 16-bit) writes into 32-bit registers.
- Python-level peripheral callbacks add overhead compared to native C QEMU device models.

## 📦 Target
- **Peripheral Base**: `0x40010000` (Size: 4 KB)
- **Registers**: CR (`0x00`), SR (`0x04`), DIN (`0x08`), DOUT (`0x0C`)
- **Simulated Action**: Hash calculation over string `KEY!` -> Digest `0x1337BEEB`

## 🔗 Resources
- AvatarPeripheral Base Class Reference (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Modeling Embedded Hardware in Python (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Principles of Memory-Mapped I/O Design (https://en.wikipedia.org/wiki/Memory-mapped_I/O)

**Runnable source, run log & report**: [`08_python_peripheral_modeling_mmio`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/08_python_peripheral_modeling_mmio)

#Avatar2 #MMIO #HardwareEmulation #PythonSecurity #ReverseEngineering #Embedded
