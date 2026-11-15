# ⚡️ 🖥 Full-System ARM Cortex-M Emulation on a Live QEMU Machine with Avatar2 Framework (Python practice)
_Post 06/30 · Avatar2 firmware orchestration playbook_

While standalone CPU emulators handle basic opcode execution, real-world embedded firmware relies on system timers, interrupt controllers, and board-level memory hierarchies. Avatar2's `QemuTarget` harnesses full-system QEMU (`qemu-system-arm`) to provide complete microcontroller system virtualization.

## 🧠 Core Concept
- **Full-System QEMU Virtualization**: Emulating not just CPU cores, but interrupt controllers (NVIC), buses, and timers.
- **Board Profile Selection**: Instantiating standardized embedded board machine models (e.g., `lm3s6965evb`).
- **QMP Protocol Communication**: Programmatic control over QEMU internal state, snapshots, and runtime device configuration.
- **Kernel / Firmware Ingestion**: Loading raw binary images or ELF kernels into virtual ROM address spaces.
- **Bus Interception Foundation**: Preparing memory layouts for dynamic forwarding when firmware touches custom peripherals.

## 💻 Key Calls
```python
gdb_port = free_port()
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="qemu_cortex_m3")
target.update_state(TargetStates.STOPPED)
ava.add_memory_range(FLASH_BASE, FLASH_SIZE, name="qemu_flash", permissions="r-x")
ava.add_memory_range(SRAM_BASE, SRAM_SIZE, name="qemu_sram", permissions="rwx")
ava.add_memory_range(MMIO_BASE, MMIO_SIZE, name="qemu_mmio", permissions="rw-")
ava.init_targets()
simulate_configuration()
firmware = build_firmware()
```

## 🔥 Use Cases
- Running complete embedded RTOS kernels (FreeRTOS, Zephyr) with virtual system timers.
- Analyzing multi-stage bootloader firmware images across real bus topologies.
- Validating cross-compiled firmware before deploying onto physical microcontroller hardware.
- Conducting full-system firmware vulnerability research with standard gdb attachments.
- Developing complex peripheral models before physical silicon is fabricated.

## ⚠️ Caveats
- QEMU system emulation requires the host machine to have `qemu-system-arm` installed and in PATH.
- Standard QEMU machine types have rigid memory layouts; mismatching your firmware's linker script causes boot faults.
- QEMU TCG optimizes basic blocks, which can alter timing assumptions in cycle-accurate firmware.
- Firmware touching unmodeled board peripherals will stall or trigger hard faults unless forwarded.

## 📦 Target
- **Target Board**: Texas Instruments Stellaris `lm3s6965evb`
- **CPU Architecture**: ARM Cortex-M3
- **Memory Layout**: Flash (256 KB @ `0x00000000`), SRAM (64 KB @ `0x20000000`)

## 🔗 Resources
- QEMU ARM System Emulator Documentation (https://www.qemu.org/docs/master/system/target-arm.html)
- Avatar2 QemuTarget Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/targets/qemu_target.py)
- QEMU Machine Protocol (QMP) Guide (https://wiki.qemu.org/Documentation/QMP)

**Runnable source, run log & report**: [`06_qemu_full_system_arm_target`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/06_qemu_full_system_arm_target)

#Avatar2 #QEMU #ARM #FirmwareEmulation #CortexM #EmbeddedSecurity
