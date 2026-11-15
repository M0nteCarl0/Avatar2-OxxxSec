# ⚡️ 🖥 Full-System ARM Cortex-M Emulation on a Live QEMU Machine (Python practice)

While standalone CPU emulators handle basic opcode execution, real-world embedded firmware relies on system timers, interrupt controllers, and board-level memory hierarchies.

## 🧠 Core Concept
- **Full-System QEMU Virtualization**: Emulating not just CPU cores, but interrupt controllers (NVIC), buses, and timers.
- **Board Profile Selection**: Instantiating standardized embedded board machine models (e.g., `lm3s6965evb`).
- **QMP Protocol Communication**: Programmatic control over QEMU internal state, snapshots, and runtime device configuration.
- **Kernel / Firmware Ingestion**: Loading raw binary images or ELF kernels into virtual ROM address spaces.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 06: Full-System ARM Cortex-M Emulation with QemuTarget.
Boots an assembled Cortex-M3 image on real QEMU and drives it over the GDB RSP stub."""

import socket
import struct
import subprocess

import keystone

STACK_TOP, RESET_HANDLER, LOOP_ADDR = 0x20004000, 0x40, 0x44


def build_firmware():
    """Vector table (SP + Reset_Handler) followed by a Thumb counter loop."""
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm("movs r0, #42\nloop: adds r0, #1\nb loop", addr=RESET_HANDLER)
    image = bytearray(struct.pack("<II", STACK_TOP, RESET_HANDLER | 1))
    image.extend(bytes(64 - len(image)))
    return bytes(image) + bytes(code)


def rsp(sock, payload):
    """$payload#checksum out, one reply packet in."""
    sock.sendall(("$%s#%02x" % (payload, sum(payload.encode()) & 0xFF)).encode())
    data = b""
    while b"#" not in data or len(data.split(b"#", 1)[1]) < 2:
        data += sock.recv(4096)
    sock.sendall(b"+")
    return data.split(b"$", 1)[1].split(b"#", 1)[0].decode()


def run_qemu_target_demo():
    with open("cortex_m3.bin", "wb") as handle:      # -kernel needs a file on disk
        handle.write(build_firmware())
    qemu = subprocess.Popen(["qemu-system-arm", "-M", "lm3s6965evb", "-cpu", "cortex-m3",
                             "-kernel", "cortex_m3.bin", "-S", "-gdb", "tcp::1234"])
    sock = socket.create_connection(("127.0.0.1", 1234), timeout=20)
    regs = rsp(sock, "g")
    print(f"[+] reset SP=0x{int(regs[26:34], 16):08x} PC=0x{int(regs[30:38], 16):08x}")
    rsp(sock, "Z0,%x,2" % LOOP_ADDR)                 # breakpoint inside the loop
    rsp(sock, "c")
    print(f"[+] hit R0={int(rsp(sock, 'g')[0:8], 16)} at the loop body")
    qemu.terminate()
    qemu.communicate(timeout=10)


if __name__ == "__main__":
    run_qemu_target_demo()
```

## 🔥 Use Cases
- Running complete embedded RTOS kernels (FreeRTOS, Zephyr) with virtual system timers.
- Analyzing multi-stage bootloader firmware images across real bus topologies.
- Validating cross-compiled firmware before deploying onto physical microcontroller hardware.

## ⚠️ Caveats & Responsible Practice
- QEMU system emulation requires the host machine to have `qemu-system-arm` installed and in PATH.
- Standard QEMU machine types have rigid memory layouts; mismatching your firmware's linker script causes boot faults.
- QEMU TCG optimizes basic blocks, which can alter timing assumptions in cycle-accurate firmware.

## 📦 Test Data & Sample Binaries
- **Target Board**: Texas Instruments Stellaris `lm3s6965evb`
- **CPU Architecture**: ARM Cortex-M3
- **Memory Layout**: Flash (256 KB @ `0x00000000`), SRAM (64 KB @ `0x20000000`)

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #QEMU #ARM #FirmwareEmulation #CortexM #EmbeddedSecurity
