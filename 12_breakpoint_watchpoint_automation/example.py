#!/usr/bin/env python3
"""
Post 12: Automated Dynamic Breakpoints & Memory Access Watchpoints
Real execution breakpoints and data watchpoints on a live Cortex-M3 firmware loop.
"""

import shutil
import tempfile

import capstone
import keystone
import unicorn
from unicorn import arm_const as uc_arm

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE = 0x08000000
RAM_BASE = 0x20000000
MEM_SIZE = 0x1000
GPIO_BASE = 0x40020000
GPIO_SIZE = 0x1000

COUNTER_ADDR = RAM_BASE          # watched variable
THRESHOLD = 3


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    code, _ = ks.asm(
        """
        ldr  r4, =0x20000000      @ counter variable in RAM
        movs r0, #0
    loop:
        adds r0, r0, #1
        str  r0, [r4]             @ watched memory write
        cmp  r0, #3
        bne  loop
        ldr  r5, =0x40020000      @ board GPIO/status register
        str  r0, [r5]             @ software breakpoint target
        b    .
        """
    )
    return bytes(code)


def run_breakpoint_watchpoint_demo() -> None:
    print("[*] Initializing Breakpoint & Watchpoint Automation...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_bp_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="cpu")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
        ava.add_memory_range(GPIO_BASE, GPIO_SIZE, name="gpio", permissions="rw-")
        ava.init_targets()
        print("[+] Avatar2 target and memory map ready")

        image = assemble_firmware()

        # Locate the two interesting program points with Capstone
        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
        instructions = list(md.disasm(image, FLASH_BASE))
        gpio_addr = [i.address for i in instructions
                     if i.mnemonic == "str" and "[r5" in i.op_str][0]
        loop_addr = [i.address for i in instructions if i.mnemonic == "adds"][0]
        print(f"[+] Watchpoint variable : 0x{COUNTER_ADDR:08x}")
        print(f"[+] Breakpoint (GPIO)   : 0x{gpio_addr:08x}")
        print(f"[+] Loop body entry     : 0x{loop_addr:08x}")

        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_map(GPIO_BASE, GPIO_SIZE)
        uc.mem_write(FLASH_BASE, image)

        hits = {"breakpoint": 0, "watchpoint": 0, "watch_values": []}

        # --- Watchpoint: real data-access hook on the counter variable ---
        def watchpoint_hook(uc_handle, access, address, size, value, _user_data):
            hits["watchpoint"] += 1
            hits["watch_values"].append(value)
            print(f"[WATCHPOINT] Write of {value} to 0x{address:08x} "
                  f"(PC: 0x{uc_handle.reg_read(uc_arm.UC_ARM_REG_PC):08x})")
            return True

        uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, watchpoint_hook,
                    begin=COUNTER_ADDR, end=COUNTER_ADDR + 3)

        # --- Breakpoint: real execution hook that halts the target at the GPIO store ---
        def breakpoint_hook(uc_handle, address, size, _user_data):
            hits["breakpoint"] += 1
            print(f"[BREAKPOINT HIT] PC=0x{address:08x} R0={uc_handle.reg_read(uc_arm.UC_ARM_REG_R0)} "
                  f"-> halting target")
            uc_handle.emu_stop()

        uc.hook_add(unicorn.UC_HOOK_CODE, breakpoint_hook, begin=gpio_addr, end=gpio_addr + 3)

        print("[*] Resuming target with breakpoints/watchpoints armed...")
        uc.emu_start(FLASH_BASE | 1, 0, count=500)

        counter = int.from_bytes(bytes(uc.mem_read(COUNTER_ADDR, 4)), "little")
        print(f"[+] Watchpoint hits     : {hits['watchpoint']} (values: {hits['watch_values']})")
        print(f"[+] Breakpoint hits     : {hits['breakpoint']}")
        print(f"[+] Counter value in RAM: {counter}")
        print(f"[+] Halted PC           : 0x{uc.reg_read(uc_arm.UC_ARM_REG_PC):08x}")

        assert hits["watchpoint"] == THRESHOLD, "watchpoint missed some writes"
        assert hits["watch_values"] == [1, 2, 3], "watchpoint observed unexpected values"
        assert hits["breakpoint"] == 1, "execution breakpoint did not trigger exactly once"
        assert counter == THRESHOLD
        assert uc.reg_read(uc_arm.UC_ARM_REG_PC) == gpio_addr

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Breakpoint and watchpoint automation verified on real execution.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_breakpoint_watchpoint_demo()
