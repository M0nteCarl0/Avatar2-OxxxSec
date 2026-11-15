# ⚡️ 📟 Virtual UART Serial Console & Telemetry Capture with Avatar2 Framework (Python practice)

During bootup, almost every embedded microcontroller transmits debug logs, bootloader banners, and runtime diagnostics through a Universal Asynchronous Receiver-Transmitter (UART) serial port. When analyzing firmware without physical serial pins attached, modeling a virtual UART peripheral allows researchers to intercept `printf` characters as they are written to the UART Data Register (DR), reconstruct output strings in memory, and capture essential system telemetry in real time.

## 🧠 Core Concept
- **UART Architecture Emulation**: Modeling the standard PL011 / STM32 USART register interface.
- **Data Register (DR) Interception**: Capturing transmitted TX bytes and queuing incoming RX bytes.
- **Flag Register (FR) Status Simulation**: Emulating Transmit FIFO Empty (`TXFE`) and Receive FIFO Not Empty (`RXNE`) flags.
- **Real-Time String De-packetization**: Buffering raw byte writes and decoding ASCII newline-delimited log strings.
- **Two-Way Interactive Shells**: Injecting operator commands into the guest firmware's serial command-line interpreter.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""
Post 09: Virtual UART Serial Console & Telemetry Capture
Modeling an ARM PL011 UART while a real Cortex-M3 core (Unicorn JIT) streams firmware logs into it.
"""

import shutil
import tempfile

import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget
from avatar2.peripherals import AvatarPeripheral

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
UART_BASE = 0x4000C000
MEM_SIZE = 0x1000
UART_SIZE = 0x1000
BANNER_OFFSET = 0x200


class VirtualPL011UART(AvatarPeripheral):
    """
    Simulates an ARM PrimeCell PL011 UART peripheral.
    Registers:
      0x00: UARTDR (Data Register - Read RX / Write TX)
      0x18: UARTFR (Flag Register - Status flags)
    """
    UARTFR_TXFE = (1 << 7)  # Transmit FIFO Empty
    UARTFR_RXFE = (1 << 4)  # Receive FIFO Empty

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.read_handler[0x00:0x04] = self.read_dr
        self.write_handler[0x00:0x04] = self.write_dr
        self.read_handler[0x18:0x1C] = self.read_fr

        self.tx_buffer = bytearray()
        self.rx_queue = bytearray(b"help")
        self.log_lines = []

    def read_dr(self, offset, size, pc=0):
        if self.rx_queue:
            return self.rx_queue.pop(0)
        return 0

    def write_dr(self, offset, size, value, pc=0):
        char = value & 0xFF
        self.tx_buffer.append(char)
        if char == 10:  # newline terminates a console line
            line = self.tx_buffer.decode("utf-8", errors="replace").strip()
            print(f"[UART CONSOLE OUT] {line}")
            self.log_lines.append(line)
            self.tx_buffer.clear()
        return True

    def read_fr(self, offset, size, pc=0):
        flags = self.UARTFR_TXFE  # Always ready to transmit
        if not self.rx_queue:
            flags |= self.UARTFR_RXFE
        return flags


def build_uart_firmware(banner: str):
    """Assemble a firmware blob that polls UARTFR and streams a banner byte-by-byte."""
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    asm = """
        ldr  r4, =0x4000C000     @ UART base address
        ldr  r5, =0x08000200     @ banner located in flash
    loop:
        ldrb r0, [r5]
        cmp  r0, #0
        beq  done
        ldr  r1, [r4, #0x18]     @ poll UARTFR (TX FIFO empty?)
        tst  r1, #0x80
        beq  loop                @ not ready -> retry
        str  r0, [r4]            @ UARTDR <- character
        adds r5, #1
        b    loop
    done:
        b    done
    """
    code, _ = ks.asm(asm)
    image = bytearray(code)
    image.extend(bytes(BANNER_OFFSET - len(image)))
    image.extend(banner.encode() + bytes(1))
    return bytes(image), FLASH_BASE + BANNER_OFFSET


def run_uart_telemetry_demo() -> None:
    print("[*] Initializing Virtual UART Telemetry Capture...")

    boot_banner = chr(10).join([
        "[*] Bootloader v2.4.1 (Cortex-M3) initializing...",
        "[+] CPU clock 72 MHz | SRAM 64 KB | Flash 256 KB",
        "[+] Peripheral bus clock initialized: OK",
        "[!] Warning: integrity check bypassed in debug build",
        "[+] Entered main operational loop. Type 'help' for console.",
        "",
    ])

    image, banner_addr = build_uart_firmware(boot_banner)
    print(f"[+] Assembled firmware blob: {len(image)} bytes, banner at 0x{banner_addr:08x}")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_uart_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="mcu_core")
        target.update_state(TargetStates.STOPPED)

        # Map the UART MMIO window and forward it to our Python peripheral model
        uart = VirtualPL011UART("pl011_uart", UART_BASE, UART_SIZE)
        ava.add_memory_range(UART_BASE, UART_SIZE, name="uart_mmio", permissions="rw-",
                             forwarded=True, forwarded_to=uart)
        ava.init_targets()
        print(f"[+] Avatar2 peripheral model 'pl011_uart' mapped at 0x{UART_BASE:08x}")

        # --- Real CPU: the firmware loop is genuinely executed by the Unicorn JIT engine ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(UART_BASE, UART_SIZE)
        uc.mem_write(FLASH_BASE, image)
        # Status registers are pre-seeded in the emulated window (RX empty + TX FIFO empty),
        # so the firmware's polling loop terminates; data writes are hooked below.
        uc.mem_write(UART_BASE + 0x18, bytes([VirtualPL011UART.UARTFR_TXFE | VirtualPL011UART.UARTFR_RXFE, 0, 0, 0]))
        uc.reg_write(uc_arm.UC_ARM_REG_SP, RAM_BASE + MEM_SIZE)

        mmio_hits = []

        def uart_write_hook(uc_handle, access, address, size, value, _user_data):
            mmio_hits.append((address, size, value))
            uart.write_memory(address, size, value, pc=uc_handle.reg_read(uc_arm.UC_ARM_REG_PC))
            return True

        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, uart_write_hook, begin=UART_BASE, end=UART_BASE + UART_SIZE - 1)

        print("[*] Streaming firmware serial output through the virtual UART...")
        uc.emu_start(FLASH_BASE | 1, 0, count=200000)

        print(f"[+] Captured {len(uart.log_lines)} complete lines of firmware telemetry.")
        print(f"[+] Real MMIO transactions observed: {len(mmio_hits)}")

        assert mmio_hits, "Firmware never touched the UART data register"
        assert any("Bootloader" in line for line in uart.log_lines), "Boot banner not captured"
        assert len(uart.log_lines) == boot_banner.strip().count(chr(10)) + 1

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Virtual UART telemetry capture verified on real executed firmware.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_uart_telemetry_demo()
```

## 🔥 Use Cases
- Capturing runtime panic traces and assertion failure logs from stripped firmware.
- Automated scraping of compile-time Git commit hashes and build dates from boot banners.
- Fuzzing embedded command-line shells (BusyBox, U-Boot CLI) over simulated serial terminals.
- Bypassing interactive password prompts by pre-loading serial RX FIFO queues with credentials.
- Recording complete communication transcripts for compliance and security auditing.

## ⚠️ Caveats & Responsible Practice
- Firmware checking baud rate divisor registers (`UARTIBRD`) must receive non-zero values to avoid division-by-zero faults.
- Ensure the flag register reports `TXFE` (Transmit FIFO Empty); otherwise firmware loops waiting forever in serial polling loops.
- Handle multi-byte UTF-8 sequences properly when decoding guest log streams.
- Some firmware uses interrupt-driven UART rather than busy-wait polling; see Post 14 for NVIC interrupt injection.
- Status registers are pre-seeded in the emulated MMIO window and data writes are intercepted by a hook, mirroring what a patched avatar-qemu does at the KVM/QEMU boundary.

## 📦 Test Data & Sample Binaries / Targets
- **Peripheral Model**: ARM PrimeCell PL011 UART
- **Base Address**: `0x4000C000` (Size: 4 KB)
- **Registers**: Data Register `UARTDR (0x00)`, Flag Register `UARTFR (0x18)`

## 🔗 Resources
- ARM PrimeCell UART (PL011) Technical Reference Manual (https://developer.arm.com/documentation/ddi0183/latest)
- Avatar2 Peripheral Modeling Documentation (https://avatar2.readthedocs.io/en/latest/api/peripherals.html)
- Embedded Serial Console Analysis Guide (https://wiki.securityheads.io/hardware-hacking/serial-uart)
- **Full repository**: [Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook](https://github.com/M0nteCarl0/Avatar2-OxxxSec) — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #UART #SerialConsole #FirmwareAnalysis #PL011 #EmbeddedSecurity
