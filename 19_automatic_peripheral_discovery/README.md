# ⚡️ 🔍 Automated Unknown Peripheral Address Discovery & Mapping with Avatar2 Framework (Python practice)
_Post 19/30 · Avatar2 firmware orchestration playbook_

Security analysts frequently receive raw, stripped firmware blobs extracted from unknown microcontrollers where complete datasheets and memory maps are unavailable. Running such firmware in an emulator immediately causes memory faults because the CPU accesses unknown peripheral registers.

## 🧠 Core Concept
- **Unmapped MMIO Fault Trapping**: Intercepting page faults triggered when firmware touches unmapped addresses.
- **Fault Telemetry Recording**: Capturing access type (Read/Write), access width (8/16/32-bit), data values, and guest `PC`.
- **Access Pattern Classification**: Differentiating status registers (repeated reads) from control registers (infrequent writes).
- **Automated Address Clustering**: Grouping discrete register accesses into standard 1KB / 4KB peripheral blocks.
- **Layout Generation**: Synthesizing clean Python `AvatarPeripheral` scaffold code directly from access logs.

## 💻 Key Calls
```python
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="cpu")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
bus = VirtualBusFabric("bus", BUS_BASE, BUS_SIZE, KNOWN_DEVICES)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
```

## 🔥 Use Cases
- Triaging unknown IoT firmware images extracted from black-box microcontroller chips.
- Identifying base addresses of debug UARTs and logging interfaces in proprietary binaries.
- Generating skeleton `AvatarPeripheral` model code automatically from execution traces.
- Detecting undocumented hardware registers and test interfaces left in production firmware.
- Mapping MMIO address spaces for Ghidra and IDA Pro symbol table importation.

## ⚠️ Caveats
- If an unmapped read returns default zero, firmware may stall in infinite polling loops waiting for a non-zero ready bit.
- Firmware may execute different initialization sequences depending on the values returned by discovery reads.
- Register offsets accessed only during error states won't appear unless error conditions are triggered.
- Differentiate between peripheral MMIO (typically `0x40000000`-`0x5FFFFFFF`) and system control registers (`0xE0000000`+).

## 📦 Target
- **Simulated Binary**: Stripped ARM Cortex-M Firmware Blob
- **Discovered Block 1**: `0x4000C000` (UART TX + Status Register)
- **Discovered Block 2**: `0x40011000` (Timer Counter & Config)

## 🔗 Resources
- Automated Hardware Model Generation Techniques (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- HALucinator: Firmware Re-hosting through Hardware Abstraction Layer Interception (https://www.usenix.org/conference/usenixsecurity20/presentation/clements)
- ARM Cortex-M System Address Map (https://developer.arm.com/documentation/dui0552/a/the-cortex-m3-processor/memory-model)

**Runnable source, run log & report**: [`19_automatic_peripheral_discovery`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/19_automatic_peripheral_discovery)

#Avatar2 #FirmwareReversing #PeripheralDiscovery #IoT #ReverseEngineering #HardwareHacking
