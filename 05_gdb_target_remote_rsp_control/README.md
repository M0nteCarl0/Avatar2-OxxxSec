# ⚡️ 🛰 GDB Remote Serial Protocol (RSP) Target Control & Instrumentation (Python practice)

The GDB Remote Serial Protocol (RSP) is the universal lingua franca of embedded systems debugging.

## 🧠 Core Concept
- **GDB RSP Socket Abstraction**: Packetized command/response exchanges (`$g#`, `$m...#`, `$c#`) managed under the hood.
- **Target Lifecycle Synchronization**: Coordinating `cont`, `step`, and breakpoint traps over remote sockets.
- **Register Bank Deserialization**: Parsing architecture-specific hex register strings into structured Python attributes.
- **Non-Stop Debugging Mode**: Interacting with multi-core target threads asynchronously without global freezes.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 05: GDB Remote Serial Protocol (RSP) Target Control & Instrumentation.
Speaks raw RSP frames ($g/$P/$m/$M/$Z0/$c) to a live gdbstub."""

import socket

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, SRAM_BASE, REG_PC = 0x00000000, 0x20000000, 15


class GdbRemoteClient:
    """Minimal RSP client: $payload#checksum framing with ACK handling."""

    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=15)
        self.buffer = b""

    def send(self, payload):
        self.sock.sendall(("$%s#%02x" % (payload, sum(payload.encode()) & 0xFF)).encode())
        while b"#" not in self.buffer or len(self.buffer.split(b"#", 1)[1]) < 2:
            self.buffer += self.sock.recv(4096)
        reply, _, tail = self.buffer[1:].partition(b"#")
        self.buffer, _ = tail[2:], self.sock.sendall(b"+")
        return reply.decode(errors="replace")


def run_gdb_target_demo(port=3333):
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="gdb_remote_target")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, 0x40000, name="firmware_rom", permissions="r-x")
    ava.init_targets()

    client = GdbRemoteClient("127.0.0.1", port)
    print(f"[+] $g  PC=0x{int(client.send('g')[30:38], 16):08x}")
    client.send("M%x,%x:%s" % (SRAM_BASE, 4, b"RSP!".hex()))     # $M into SRAM
    print(f"[+] $m  {bytes.fromhex(client.send('m%x,%x' % (SRAM_BASE, 4)))!r}")
    client.send("Z0,%x,2" % 0x44)                # hardware breakpoint
    client.send("c")                             # resume until the trap
    print(f"[+] trap PC=0x{int(client.send('g')[30:38], 16):08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_gdb_target_demo()
```

## 🔥 Use Cases
- Automated headless regression testing over OpenOCD and Black Magic Probe hardware dongles.
- Dynamic breakpoint orchestration during vulnerability triage of proprietary firmware.
- Scripted extraction of decrypted firmware payloads directly from device RAM over SWD.

## ⚠️ Caveats & Responsible Practice
- Network latency on GDB RSP sockets directly impacts single-stepping throughput.
- Ensure the remote gdbserver implementation supports target XML memory maps (`qXfer:memory-map:read`).
- Hardware breakpoints on ARM Cortex-M are typically limited by silicon to 4 or 6 FPB units.

## 📦 Test Data & Sample Binaries
- **Protocol**: GDB Remote Serial Protocol (RSP)
- **Endpoint**: `127.0.0.1:3333`
- **Target Registers**: `PC=0x08001234`, `SP=0x20003FE0`, `R0=0xDEADBEEF`

## 🔗 Resources
- GDB Remote Serial Protocol Specification (https://sourceware.org/gdb/current/onlinedocs/gdb.html/Remote-Protocol.html)
- Avatar2 GDB Protocol Implementation (https://github.com/avatartwo/avatar2/blob/master/avatar2/protocols/gdb.py)

**Full script, run log & report**: [`05_gdb_target_remote_rsp_control/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/05_gdb_target_remote_rsp_control)

#Avatar2 #GDB #RSP #FirmwareDebugging #HardwareHacking #ReverseEngineering
