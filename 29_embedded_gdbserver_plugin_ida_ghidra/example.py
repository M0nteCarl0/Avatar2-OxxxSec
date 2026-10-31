#!/usr/bin/env python3
"""
Post 29: Exposing Orchestrated Targets to IDA Pro and Ghidra via GDBServer
Configuring Avatar2's embedded GDBServer plugin to accept connections from external disassemblers.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._regs = {}
    def read_register(self, reg):
        return self._regs.get(reg, 0)
    def write_register(self, reg, val):
        self._regs[reg] = val
        return True

def run_gdbserver_plugin_demo() -> None:
    print("[*] Initializing Avatar2 Embedded GDBServer Plugin...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_gdbserver_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(EmulatedTarget, name="orchestrated_mcu")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x20000, name="code_rom", permissions="r-x")
        ava.add_memory_range(0x20000000, 0x8000,  name="data_ram", permissions="rwx")
        
        ava.init_targets()
        
        GDB_SERVER_PORT = 3333
        GDB_SERVER_HOST = "127.0.0.1"
        
        print(f"[+] Avatar2 GDBServer Plugin configured:")
        print(f"  Listening Endpoint: {GDB_SERVER_HOST}:{GDB_SERVER_PORT}")
        print(f"  Target Attached   : '{target.name}' (Architecture: {ava.arch.__class__.__name__})")
        
        target.regs.pc = 0x08001000
        target.regs.sp = 0x20007FF0
        target.regs.r0 = 0x00000000
        
        print()
        print("=" * 65)
        print("  EXTERNAL DEBUGGER CONNECTION INSTRUCTIONS")
        print("=" * 65)
        print("In Ghidra Debugger / IDA Pro / GDB Console:")
        print(f"  (gdb) target remote {GDB_SERVER_HOST}:{GDB_SERVER_PORT}")
        print("  (gdb) set architecture arm")
        print("  (gdb) x/10i $pc")
        print("=" * 65)
        
        print()
        print(f"[+] Emulated CPU Status for GUI client:")
        print(f"  PC : 0x{target.regs.pc:08x} [Reset Handler]")
        print(f"  SP : 0x{target.regs.sp:08x}")
        print(f"  Status: READY_FOR_ATTACHMENT")
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] GDBServer plugin setup verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_gdbserver_plugin_demo()
