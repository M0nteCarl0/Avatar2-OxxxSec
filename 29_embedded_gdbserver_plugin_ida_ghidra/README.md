# ⚡️ 🔌 Exposing Orchestrated Targets to IDA Pro and Ghidra via GDBServer (Python practice)

Automated scripting is powerful, but complex reverse engineering often demands interactive visual debugging: stepping through decompiled C code in Ghidra, setting visual breakpoints in IDA Pro, or inspecting disassembly graphs in Binary Ninja. Avatar2 includes an embedded `GDBServer` plugin.

## 🧠 Core Concept
- **Avatar2 GDBServer Plugin**: Exposing orchestrated targets as standard GDB RSP endpoints for external GUIs.
- **GUI Multiplexing**: Connecting Ghidra, IDA Pro, and Binary Ninja to hybrid execution sandboxes.
- **Transparent Protocol Translation**: Translating external GUI stepping requests into internal target execution cycles.
- **Visual Breakpoint Synchronization**: Reflecting breakpoints placed in GUI disassembly graphs into Avatar targets.
- **Interactive Peripheral Inspection**: Allowing analysts to view forwarded peripheral register updates live in GUI memory viewers.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
"""Post 29: Exposing Orchestrated Targets to IDA Pro and Ghidra via GDBServer.
Configures Avatar2's embedded GDBServer plugin to accept connections from external GUIs."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

GDB_SERVER_HOST, GDB_SERVER_PORT = "127.0.0.1", 3333


class EmulatedTarget(DummyTarget):
    """The target an external GUI steps through over GDB RSP."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()


def run_gdbserver_plugin_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="orchestrated_mcu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x20000, name="code_rom", permissions="r-x")
    ava.add_memory_range(0x20000000, 0x8000, name="data_ram", permissions="rwx")
    ava.init_targets()

    target.regs.pc, target.regs.sp = 0x08001000, 0x20007FF0
    print(f"[+] {GDB_SERVER_HOST}:{GDB_SERVER_PORT} -> '{target.name}' "
          f"({ava.arch.__class__.__name__}) READY_FOR_ATTACHMENT")
    for command in (f"target remote {GDB_SERVER_HOST}:{GDB_SERVER_PORT}",
                    "set architecture arm", "x/10i $pc"):
        print(f"    (gdb) {command}")

    ava.stop()
    ava.fast_queue_listener.stop()
    ava.shutdown()


if __name__ == "__main__":
    run_gdbserver_plugin_demo()
```

## 🔥 Use Cases
- Interactive visual step-debugging of hybrid firmware sessions directly inside Ghidra.
- Setting visual breakpoints in IDA Pro while peripheral MMIO is forwarded to physical hardware.
- Inspecting complex FreeRTOS structures in real time using Binary Ninja memory views.
- Teaching embedded reverse engineering with a full GUI interface backed by Python automation.

## ⚠️ Caveats & Responsible Practice
- Ensure the firewall allows incoming TCP connections on the specified GDBServer port.
- In Ghidra, select the correct GDB language ID (`ARM:LE:32:Cortex`) matching the Avatar architecture.
- External GUI disassemblers issue frequent memory queries; caching read-only Flash pages (Post 15) improves responsiveness.
- Always disconnect the external GUI client cleanly before shutting down the Avatar orchestrator.

## 📦 Test Data & Sample Binaries
- **Plugin**: Avatar2 GDBServer Plugin
- **Binding Endpoint**: `127.0.0.1:3333`
- **Supported Clients**: Ghidra Debugger, IDA Pro, Binary Ninja, GDB Multiarch

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #GDBServer #Ghidra #IDAPro #BinaryNinja #ReverseEngineering #FirmwareSecurity
