# ⚡️ 📟 Virtual UART Serial Console & Telemetry Capture (Python practice)

During bootup, almost every embedded microcontroller transmits debug logs, bootloader banners, and runtime diagnostics through a Universal Asynchronous Receiver-Transmitter (UART) serial port.

## 🧠 Core Concept
- **UART Architecture Emulation**: Modeling the standard PL011 / STM32 USART register interface.
- **Data Register (DR) Interception**: Capturing transmitted TX bytes and queuing incoming RX bytes.
- **Flag Register (FR) Status Simulation**: Emulating Transmit FIFO Empty (`TXFE`) and Receive FIFO Not Empty (`RXNE`) flags.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 09: Virtual UART Serial Console & Telemetry Capture.
Models an ARM PL011 UART that captures firmware telemetry byte by byte."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

UART_BASE, UART_SIZE, UARTDR, UARTFR, TXFE = 0x4000C000, 0x1000, 0x00, 0x18, 0x80
BANNER = b"Bootloader v2.4.1 | CPU 72 MHz | SRAM 64 KB\r\n"


class VirtualPL011UART(AvatarPeripheral):
    """TXFE is always asserted, so the guest polling loop streams at full speed."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.captured = bytearray()

    def read(self, offset, size):
        return TXFE if offset == UARTFR else 0

    def write(self, offset, size, value):
        if offset == UARTDR:                         # firmware serial output
            self.captured.append(value & 0xFF)
            print(chr(value & 0xFF), end="", flush=True)
        return True


def run_uart_telemetry_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="mcu_core")
    target.update_state(TargetStates.STOPPED)
    uart = VirtualPL011UART("pl011_uart", UART_BASE, UART_SIZE)
    ava.add_memory_range(UART_BASE, UART_SIZE, name="uart_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=uart)
    ava.init_targets()

    print("[*] guest polls UARTFR (TXFE set) and stores the banner into UARTDR")
    for byte in BANNER:
        assert uart.read(UARTFR, 4) & TXFE           # FIFO always ready
        uart.write(UARTDR, 1, byte)
    print(f"\n[+] captured {len(uart.captured)} bytes of telemetry")
    ava.shutdown()


if __name__ == "__main__":
    run_uart_telemetry_demo()
```

## 🔥 Use Cases
- Capturing runtime panic traces and assertion failure logs from stripped firmware.
- Automated scraping of compile-time Git commit hashes and build dates from boot banners.
- Fuzzing embedded command-line shells (BusyBox, U-Boot CLI) over simulated serial terminals.

## ⚠️ Caveats & Responsible Practice
- Firmware checking baud rate divisor registers (`UARTIBRD`) must receive non-zero values to avoid division-by-zero faults.
- Ensure the flag register reports `TXFE` (Transmit FIFO Empty); otherwise firmware loops waiting forever in serial polling loops.

## 📦 Test Data & Sample Binaries
- **Peripheral Model**: ARM PrimeCell PL011 UART
- **Base Address**: `0x4000C000` (Size: 4 KB)
- **Registers**: Data Register `UARTDR (0x00)`, Flag Register `UARTFR (0x18)`

## 🔗 Resources
- ARM PrimeCell UART (PL011) Technical Reference Manual (https://developer.arm.com/documentation/ddi0183/latest)
- Avatar2 Peripheral Modeling Documentation (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)

**Full script, run log & report**: [`09_virtual_uart_serial_telemetry/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/09_virtual_uart_serial_telemetry)

#Avatar2 #UART #SerialConsole #FirmwareAnalysis #PL011 #EmbeddedSecurity
