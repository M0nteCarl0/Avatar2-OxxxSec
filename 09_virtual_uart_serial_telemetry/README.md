# ⚡️ 📟 Virtual UART Serial Console & Telemetry Capture with Avatar2 Framework (Python practice)
_Post 09/30 · Avatar2 firmware orchestration playbook_

During bootup, almost every embedded microcontroller transmits debug logs, bootloader banners, and runtime diagnostics through a Universal Asynchronous Receiver-Transmitter (UART) serial port.

## 🧠 Core Concept
- **UART Architecture Emulation**: Modeling the standard PL011 / STM32 USART register interface.
- **Data Register (DR) Interception**: Capturing transmitted TX bytes and queuing incoming RX bytes.
- **Flag Register (FR) Status Simulation**: Emulating Transmit FIFO Empty (`TXFE`) and Receive FIFO Not Empty (`RXNE`) flags.
- **Real-Time String De-packetization**: Buffering raw byte writes and decoding ASCII newline-delimited log strings.
- **Two-Way Interactive Shells**: Injecting operator commands into the guest firmware's serial command-line interpreter.

## 💻 Key Calls
```python
image, banner_addr = build_uart_firmware(boot_banner)
ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
target = ava.add_target(DummyTarget, name="mcu_core")
target.update_state(TargetStates.STOPPED)
uart = VirtualPL011UART("pl011_uart", UART_BASE, UART_SIZE)
ava.init_targets()
uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch, ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
uc.mem_map(FLASH_BASE, MEM_SIZE)
uc.mem_map(RAM_BASE, MEM_SIZE)
uc.mem_map(UART_BASE, UART_SIZE)
```

## 🔥 Use Cases
- Capturing runtime panic traces and assertion failure logs from stripped firmware.
- Automated scraping of compile-time Git commit hashes and build dates from boot banners.
- Fuzzing embedded command-line shells (BusyBox, U-Boot CLI) over simulated serial terminals.
- Bypassing interactive password prompts by pre-loading serial RX FIFO queues with credentials.
- Recording complete communication transcripts for compliance and security auditing.

## ⚠️ Caveats
- Firmware checking baud rate divisor registers (`UARTIBRD`) must receive non-zero values to avoid division-by-zero faults.
- Ensure the flag register reports `TXFE` (Transmit FIFO Empty); otherwise firmware loops waiting forever in serial polling loops.
- Handle multi-byte UTF-8 sequences properly when decoding guest log streams.
- Some firmware uses interrupt-driven UART rather than busy-wait polling; see Post 14 for NVIC interrupt injection.

## 📦 Target
- **Peripheral Model**: ARM PrimeCell PL011 UART
- **Base Address**: `0x4000C000` (Size: 4 KB)
- **Registers**: Data Register `UARTDR (0x00)`, Flag Register `UARTFR (0x18)`

## 🔗 Resources
- ARM PrimeCell UART (PL011) Technical Reference Manual (https://developer.arm.com/documentation/ddi0183/latest)
- Avatar2 Peripheral Modeling Documentation (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Embedded Serial Console Analysis Guide (https://wiki.securityheads.io/hardware-hacking/serial-uart)

**Runnable source, run log & report**: [`09_virtual_uart_serial_telemetry`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/09_virtual_uart_serial_telemetry)

#Avatar2 #UART #SerialConsole #FirmwareAnalysis #PL011 #EmbeddedSecurity
