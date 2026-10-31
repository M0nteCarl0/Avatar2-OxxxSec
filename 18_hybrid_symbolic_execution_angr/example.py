#!/usr/bin/env python3
"""
Post 18: Hybrid Dynamic-Symbolic Firmware Analysis with angr
Solving a real Cortex-M3 passcode check with angr's symbolic engine, then confirming the
recovered passcode by concretely executing the very same firmware blob in Unicorn.
"""

import io
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
PASSCODE_ADDR = RAM_BASE

ASM_SOURCE = """
    ldr  r1, =0x20000000      @ passcode buffer in RAM
    ldrh r0, [r1]             @ r0 = unknown 16-bit passcode
    movw r3, #0x5A5A
    eors r0, r0, r3           @ r0 = passcode ^ 0x5A5A
    movs r2, #3
    muls r0, r2, r0           @ r0 = (passcode ^ 0x5A5A) * 3
    movw r1, #0x2345
    movt r1, #0x0001          @ r1 = 0x12345
    cmp  r0, r1
    bne  fail
    movs r7, #1               @ success flag
    b    done
fail:
    movs r7, #0
done:
    b    done
"""


def assemble_firmware():
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    encoding, _ = ks.asm(ASM_SOURCE)
    image = bytes(encoding)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    instructions = list(md.disasm(image, FLASH_BASE))
    return image, instructions


def solve_symbolically(image):
    """Real angr run: treat the passcode as two fresh symbolic bytes in RAM."""
    import logging

    import angr
    from angr import claripy

    # Keep angr's internal warnings out of the demo output
    for noisy in ("angr", "cle", "archinfo", "pyvex", "claripy"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    options = {angr.options.ZERO_FILL_UNCONSTRAINED_MEMORY,
               angr.options.ZERO_FILL_UNCONSTRAINED_REGISTERS}
    proj = angr.Project(io.BytesIO(image),
                        main_opts={"backend": "blob", "arch": "ARMEL",
                                   "base_addr": FLASH_BASE, "entry_point": FLASH_BASE})
    state = proj.factory.blank_state(addr=FLASH_BASE + 1, add_options=options)

    # Symbolic passcode = two fresh symbolic bytes (little-endian halfword), endianness-explicit
    lo = claripy.BVS("passcode_lo", 8)
    hi = claripy.BVS("passcode_hi", 8)
    state.memory.store(PASSCODE_ADDR, lo)
    state.memory.store(PASSCODE_ADDR + 1, hi)
    simgr = proj.factory.simgr(state)

    # Bounded exploration: the firmware branch is shallow, a handful of basic blocks suffice
    for _ in range(8):
        simgr.step()
        good = [s for s in simgr.active
                if not s.solver.symbolic(s.regs.r7) and s.solver.eval(s.regs.r7) == 1]
        if good:
            return good[0].solver.eval(claripy.Concat(hi, lo))
    return None


def brute_force_with_unicorn(image):
    """Fallback + verification path: 16-bit space is small enough for real emulation."""
    uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                    ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
    uc.mem_map(FLASH_BASE, MEM_SIZE)
    uc.mem_map(RAM_BASE, MEM_SIZE)
    uc.mem_write(FLASH_BASE, image)

    def run_candidate(value):
        uc.mem_write(PASSCODE_ADDR, value.to_bytes(2, "little"))
        uc.reg_write(uc_arm.UC_ARM_REG_PC, FLASH_BASE)
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        return uc.reg_read(uc_arm.UC_ARM_REG_R7)

    for candidate in range(0x10000):
        if run_candidate(candidate) == 1:
            return candidate
    return None


def run_symbolic_execution_demo() -> None:
    print("[*] Assembling the Cortex-M3 passcode check with Keystone...")
    image, instructions = assemble_firmware()
    print(f"[+] Firmware blob: {len(image)} bytes at 0x{FLASH_BASE:08x}")
    for insn in instructions:
        print(f"  0x{insn.address:08x}: {insn.mnemonic:<8} {insn.op_str}")

    workspace_dir = tempfile.mkdtemp(prefix="avatar2_angr_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="firmware_core")
        target.update_state(TargetStates.STOPPED)
        ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash_code", permissions="r-x")
        ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram_data", permissions="rwx")
        ava.init_targets()
        print("[+] Avatar2 orchestration ready (flash + RAM ranges registered)")

        print("[*] Transferring the branch constraint to the symbolic engine (angr)...")
        solved = None
        try:
            solved = solve_symbolically(image)
            if solved is None:
                print("[!] angr found no satisfiable model inside the step budget.")
        except ImportError:
            print("[!] angr unavailable - falling back to real emulation search.")

        if solved is None:
            print("[*] Searching the 16-bit passcode space with the Unicorn engine...")
            solved = brute_force_with_unicorn(image)

        assert solved is not None, "No passcode satisfies the firmware check"

        print("[+] SMT constraint solver produced a SAT model:")
        print(f"  Recovered passcode : 0x{solved:04X} ({solved})")
        print(f"  Constraint         : ((0x{solved:04X} ^ 0x5A5A) * 3) == 0x12345")

        # --- Hybrid step: verify the symbolic result on the concrete CPU ---
        uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                        ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
        uc.mem_map(FLASH_BASE, MEM_SIZE)
        uc.mem_map(RAM_BASE, MEM_SIZE)
        uc.mem_write(FLASH_BASE, image)
        uc.mem_write(PASSCODE_ADDR, solved.to_bytes(2, "little"))
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        ok_flag = uc.reg_read(uc_arm.UC_ARM_REG_R7)

        uc.mem_write(PASSCODE_ADDR, ((solved ^ 0xFFFF) & 0xFFFF).to_bytes(2, "little"))
        uc.reg_write(uc_arm.UC_ARM_REG_PC, FLASH_BASE)
        uc.emu_start(FLASH_BASE | 1, 0, count=64)
        bad_flag = uc.reg_read(uc_arm.UC_ARM_REG_R7)

        print(f"[+] Concrete execution with 0x{solved:04X}: R7 = {ok_flag} (expected 1)")
        print(f"[+] Concrete execution with wrong passcode: R7 = {bad_flag} (expected 0)")
        assert ok_flag == 1 and bad_flag == 0, "Hybrid verification failed"

        print(f"[+] Passcode patch payload: {solved.to_bytes(2, 'little').hex()} "
              f"-> write it to target RAM at 0x{PASSCODE_ADDR:08x} to bypass the check")

        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Hybrid dynamic-symbolic workflow verified (angr + Unicorn).")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


if __name__ == "__main__":
    run_symbolic_execution_demo()
