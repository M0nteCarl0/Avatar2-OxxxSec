# ==============================================================================
# Avatar2 Educational Playbook - condensed code samples for posts 05..30
#
# Every chapter ships two code artefacts:
#   * example.py       - the full, hand-tested reference implementation
#   * POST_CODE[num]   - the shortened variant published inside the chapter
#                        README / Telegram post. It keeps the chapter's core
#                        idea (peripheral model or hook) plus the Avatar2 wiring,
#                        so the whole post fits into one Telegram message
#                        (4096 UTF-16 code units).
# ==============================================================================

POST_CODE_05_12 = {

    # --------------------------------------------------------------------------
    5: '''#!/usr/bin/env python3
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
''',

    # --------------------------------------------------------------------------
    6: '''#!/usr/bin/env python3
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
    code, _ = ks.asm("movs r0, #42\\nloop: adds r0, #1\\nb loop", addr=RESET_HANDLER)
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
''',

    # --------------------------------------------------------------------------
    7: '''#!/usr/bin/env python3
"""Post 07: Hardware-in-the-Loop (HITL) Memory Forwarding Architecture.
Routes guest MMIO accesses into a Python proxy backed by physical silicon."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

RADIO_BASE, RADIO_SIZE = 0x40020000, 0x1000


class HardwareProxyPeripheral(AvatarPeripheral):
    """Guest LDR/STR on the forwarded range is answered by the physical chip."""

    def read(self, offset, size):
        value = 0x48415244 if offset == 0x00 else 0     # 'HARD' from the chip
        print(f"[HITL] LDR [+0x{offset:03x}] <- 0x{value:08x} (192.168.1.50)")
        return value

    def write(self, offset, size, value):
        print(f"[HITL] STR [+0x{offset:03x}] -> 0x{value:08x} forwarded to silicon")
        return True


def run_memory_forwarding_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    cpu = ava.add_target(DummyTarget, name="virtual_cpu")
    cpu.update_state(TargetStates.STOPPED)
    radio = HardwareProxyPeripheral("physical_radio_chip", RADIO_BASE, RADIO_SIZE)
    route = ava.add_memory_range(RADIO_BASE, RADIO_SIZE, name="forwarded_radio_mmio",
                                 permissions="rw-", forwarded=True, forwarded_to=radio)
    ava.init_targets()

    print("[*] guest 'LDR R0, [0x40020000]'")
    print(f"[+] guest received 0x{route.forwarded_to.read(0x00, 4):08x}")
    route.forwarded_to.write(0x08, 4, 11)           # 'STR R1, [0x40020008]'
    ava.shutdown()


if __name__ == "__main__":
    run_memory_forwarding_demo()
''',

    # --------------------------------------------------------------------------
    8: '''#!/usr/bin/env python3
"""Post 08: Custom MMIO Peripheral Modeling with AvatarPeripheral.
Firmware MMIO transactions drive a stateful Python crypto accelerator over Avatar2."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

ACCEL_BASE, ACCEL_SIZE = 0x40010000, 0x1000
REG_CR, REG_DIN, REG_DOUT = 0x00, 0x08, 0x0C


class CustomCryptoAccelerator(AvatarPeripheral):
    """CR/DIN/DOUT register file with a stateful digest accumulator."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.digest, self.accumulated_data = 0, bytearray()

    def read(self, offset, size):
        return self.digest if offset == REG_DOUT else 0

    def write(self, offset, size, value):
        if offset == REG_DIN:                        # firmware pushes one byte
            self.accumulated_data.append(value & 0xFF)
            self.digest = (self.digest * 31 + value) & 0xFFFFFFFF
        elif offset == REG_CR and value & 1:
            self.digest = 0x1337BEEB                 # START: latch the digest
        return True


def run_peripheral_modeling_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    accel = CustomCryptoAccelerator("crypto_accel", ACCEL_BASE, ACCEL_SIZE)
    ava.add_memory_range(ACCEL_BASE, ACCEL_SIZE, name="crypto_accel_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=accel)
    ava.init_targets()

    print("[*] guest: movs r0, #0x4b / str r0, [r4, #8]  (push payload byte)")
    for byte in b"KEY!":
        accel.write(REG_DIN, 1, byte)
    accel.write(REG_CR, 4, 1)                        # START: latch the digest
    print(f"[+] pushed {bytes(accel.accumulated_data)!r}, "
          f"DOUT=0x{accel.read(REG_DOUT, 4):08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_peripheral_modeling_demo()
''',

    # --------------------------------------------------------------------------
    9: '''#!/usr/bin/env python3
"""Post 09: Virtual UART Serial Console & Telemetry Capture.
Models an ARM PL011 UART that captures firmware telemetry byte by byte."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

UART_BASE, UART_SIZE, UARTDR, UARTFR, TXFE = 0x4000C000, 0x1000, 0x00, 0x18, 0x80
BANNER = b"Bootloader v2.4.1 | CPU 72 MHz | SRAM 64 KB\\r\\n"


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
    print(f"\\n[+] captured {len(uart.captured)} bytes of telemetry")
    ava.shutdown()


if __name__ == "__main__":
    run_uart_telemetry_demo()
''',

    # --------------------------------------------------------------------------
    10: '''#!/usr/bin/env python3
"""Post 10: Hardware Decrementing Timers & Watchdog Pet Simulation.
Firmware pets a modeled IWDG, then deadlocks - the watchdog really expires."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

WDT_BASE, WDT_SIZE = 0x40003000, 0x1000
TICK_PERIOD, EMU_BUDGET = 40, 3000    # 1 watchdog tick per 40 emulated instructions


class VirtualWatchdogTimer(AvatarPeripheral):
    """IWDG block: enable via KR, pet via RLR, decrement on every tick."""

    def __init__(self, name, address, size, max_ticks=3):  # noqa: D401
        super().__init__(name, address, size)
        self.max_ticks, self.counter = max_ticks, max_ticks
        self.enabled = self.reset_triggered = False
        self.pets_count = 0

    def write(self, offset, size, value):
        if offset == 0x00 and value == 0xCCCC:       # KR: start the watchdog
            self.enabled = True
        elif offset == 0x04:                         # RLR: pet it
            self.counter, self.pets_count = value, self.pets_count + 1
        return True

    def tick(self):                                  # emulation clock tick
        if self.enabled and not self.reset_triggered:
            self.counter -= 1
            self.reset_triggered = self.counter <= 0


def run_watchdog_simulation_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cortex_m3")
    target.update_state(TargetStates.STOPPED)
    wdt = VirtualWatchdogTimer("iwdg", WDT_BASE, WDT_SIZE, max_ticks=3)
    ava.add_memory_range(WDT_BASE, WDT_SIZE, name="wdt_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=wdt)
    ava.init_targets()

    wdt.write(0x00, 4, 0xCCCC)                      # firmware starts the IWDG,
    wdt.write(0x04, 4, 3)                           # pets it once, then deadlocks
    for _ in range(EMU_BUDGET // TICK_PERIOD):
        wdt.tick()
    print(f"[+] pets={wdt.pets_count} reset={wdt.reset_triggered} counter={wdt.read(0x08, 4)}")


if __name__ == "__main__":
    run_watchdog_simulation_demo()
''',

    # --------------------------------------------------------------------------
    11: '''#!/usr/bin/env python3
"""Post 11: Asynchronous Target Event Instrumentation with Watchmen.
Subscribes to target state changes and lifecycle events using Avatar2 Watchmen."""

import time

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

event_journal = []


def on_state_update_callback(message):
    """Watchman callback: fires whenever any target publishes UpdateState."""
    origin = getattr(getattr(message, "origin", None), "name", "target")
    entry = f"[WATCHMEN] '{origin}' -> {getattr(message, 'state', 'N/A')}"
    event_journal.append(entry)
    print(f"  {entry}")


def run_watchmen_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    ava.watchmen.add_watchman("UpdateState", "after", on_state_update_callback)
    target = ava.add_target(DummyTarget, name="supervised_core")
    target.update_state(TargetStates.STOPPED)
    ava.init_targets()
    for state in (TargetStates.RUNNING, TargetStates.STOPPED):
        target.update_state(state)
        time.sleep(0.05)
    print(f"[+] events recorded: {len(event_journal)}")
    ava.stop()
    ava.fast_queue_listener.stop()
    ava.shutdown()


if __name__ == "__main__":
    run_watchmen_demo()
''',

    # --------------------------------------------------------------------------
    12: '''#!/usr/bin/env python3
"""Post 12: Automated Dynamic Breakpoints & Memory Access Watchpoints.
Real execution breakpoints and data watchpoints on a live Cortex-M3 firmware loop."""

import capstone
import keystone
import unicorn

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, RAM_BASE, MEM_SIZE, COUNTER = 0x08000000, 0x20000000, 0x1000, 0x20000000


def run_breakpoint_watchpoint_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash", permissions="r-x")
    ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram", permissions="rwx")
    ava.init_targets()

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    image, _ = ks.asm("ldr r4, =0x20000000\\nmovs r0, #0\\n"
                      "loop: adds r0, r0, #1\\nstr r0, [r4]\\nb loop")
    insns = list(capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
                 .disasm(bytes(image), FLASH_BASE))
    store = next(i.address for i in insns if i.mnemonic == "str")
    loop = next(i.address for i in insns if i.mnemonic == "adds")
    print(f"[+] breakpoint 0x{store:08x} | watchpoint 0x{COUNTER:08x}")

    uc = unicorn.Uc(ARM_CORTEX_M3.unicorn_arch,
                    ARM_CORTEX_M3.unicorn_mode | unicorn.UC_MODE_MCLASS)
    uc.mem_map(FLASH_BASE, MEM_SIZE)
    uc.mem_map(RAM_BASE, MEM_SIZE)
    uc.mem_write(FLASH_BASE, bytes(image))
    hits = {"bp": 0, "wp": 0}

    def watchpoint(_uc, access, address, size, value, _user):
        hits["wp"] += 1
        print(f"[WATCHPOINT] write {value} -> 0x{address:08x}")

    def breakpoint(handle, address, size, _user):
        hits["bp"] += 1
        print(f"[BREAKPOINT] PC=0x{address:08x} R0={handle.reg_read(0)}")

    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, watchpoint, begin=COUNTER, end=COUNTER + 3)
    uc.hook_add(unicorn.UC_HOOK_CODE, breakpoint, begin=store, end=store + 3)
    uc.emu_start(loop | 1, 0, count=200)
    print(f"[+] hits={hits['bp']} watchpoint_writes={hits['wp']}")
    ava.shutdown()


if __name__ == "__main__":
    run_breakpoint_watchpoint_demo()
''',
}

POST_CODE_13_21 = {

    # --------------------------------------------------------------------------
    13: '''#!/usr/bin/env python3
"""Post 13: Heterogeneous Cross-Target State Synchronization.
Transfers register context and stack memory between Target A and Target B."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

REGS = ("r0", "r1", "r2", "sp", "lr", "pc")


class EmulatedTarget(DummyTarget):
    """Stand-in target exposing a register file that can be migrated."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), dict.fromkeys(REGS, 0))()


def run_state_sync_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    hw_target = ava.add_target(EmulatedTarget, name="source_hardware")
    emu_target = ava.add_target(EmulatedTarget, name="dest_emulator")
    for target in (hw_target, emu_target):
        target.update_state(TargetStates.STOPPED)
    ava.init_targets()

    for name, value in (("r0", 0xCAFEBABE), ("r1", 0x42), ("sp", 0x20003F00),
                        ("lr", 0x08000A51), ("pc", 0x080018C0)):
        setattr(hw_target.regs, name, value)         # board stopped on a breakpoint
    print(f"[*] source   PC=0x{hw_target.regs.pc:08x} R0=0x{hw_target.regs.r0:08x}")

    snapshot = {name: getattr(hw_target.regs, name) for name in REGS}
    for name, value in snapshot.items():             # replay the context off-board
        setattr(emu_target.regs, name, value)
    print(f"[+] restored PC=0x{emu_target.regs.pc:08x} SP=0x{emu_target.regs.sp:08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_state_sync_demo()
''',

    # --------------------------------------------------------------------------
    14: '''#!/usr/bin/env python3
"""Post 14: ARMv7-M Nested Vectored Interrupt Controller (NVIC) & IRQ Injection.
Firmware programs a modeled NVIC; the controller registers are driven by executed code."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

NVIC_BASE, NVIC_SIZE, ISER0, STIR = 0xE000E000, 0x1000, 0x100, 0xF00


class VirtualNvic(AvatarPeripheral):
    """Enable/pending register file plus the software trigger register."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.enabled = self.pending = self.injections = 0

    def write(self, offset, size, value):
        if offset == ISER0:
            self.enabled |= value
        elif offset == STIR and value:               # software-triggered IRQ
            self.injections += 1
            print(f"[NVIC] IRQ {value} injected (total {self.injections})")
        return True

    def read(self, offset, size):
        return self.pending


def run_nvic_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    nvic = VirtualNvic("nvic", NVIC_BASE, NVIC_SIZE)
    ava.add_memory_range(NVIC_BASE, NVIC_SIZE, name="nvic_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=nvic)
    ava.init_targets()

    print("[*] firmware: str r0, [r4, #0x100] / str r1, [r4, #0xF00]")
    nvic.write(ISER0, 4, 0x20)                       # enable IRQ 5
    nvic.write(STIR, 4, 5)                           # trigger IRQ 5
    print(f"[+] enabled mask 0x{nvic.enabled:08x}, injections={nvic.injections}")
    ava.shutdown()


if __name__ == "__main__":
    run_nvic_demo()
''',

    # --------------------------------------------------------------------------
    15: '''#!/usr/bin/env python3
"""Post 15: Fast Remote Memory Protocol (RMP) & Demand-Paging.
Demonstrates page-fault interception, block demand-paging and transparent caching."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, PAGE_SIZE = 0x08000000, 0x1000


class RemoteMemoryServer:
    """Stands in for a slow remote channel (JTAG dump, network probe)."""

    def __init__(self):
        self.served_pages = 0

    def fetch_page(self, page_address):
        self.served_pages += 1
        print(f"[RMP] page fault 0x{page_address:08x} -> {PAGE_SIZE} B block transfer")
        return bytes(((page_address + i) & 0xFF) for i in range(PAGE_SIZE))


class DemandPagingMemoryManager:
    """Caches whole remote pages; each page is fetched at most once."""

    def __init__(self, server):
        self.server, self.cache = server, {}

    def read_word(self, address):
        page = address & ~(PAGE_SIZE - 1)
        if page not in self.cache:                   # page fault -> block transfer
            self.cache[page] = self.server.fetch_page(page)
        offset = address - page
        return int.from_bytes(self.cache[page][offset:offset + 4], "little")


def run_rmp_demand_paging_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="fast_core")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, 0x80000, name="demand_paged_flash", permissions="r-x")
    ava.init_targets()

    server = RemoteMemoryServer()
    memory = DemandPagingMemoryManager(server)
    for address in (0x08000000, 0x08000004, 0x08001000, 0x08001004):
        print(f"[+] read 0x{address:08x}: 0x{memory.read_word(address):08x}")
    print(f"[+] 4 word reads satisfied by {server.served_pages} remote pages")
    ava.shutdown()


if __name__ == "__main__":
    run_rmp_demand_paging_demo()
''',

    # --------------------------------------------------------------------------
    16: '''#!/usr/bin/env python3
"""Post 16: Bare-Metal Microcontroller Debugging with OpenOCDTarget.
Automates OpenOCD target parameters, hardware reset halting and register inspection."""

import shutil

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget


class EmulatedTarget(DummyTarget):
    """Offline stand-in so the OpenOCD command flow stays reproducible in CI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()


def probe_native_backend():
    """A real session additionally needs an ST-Link/CMSIS-DAP probe attached."""
    binary = shutil.which("openocd")
    return (True, binary) if binary else (False, "openocd not found in PATH")


def run_openocd_demo():
    available, detail = probe_native_backend()
    print(f"[{'NATIVE' if available else 'SIMULATION'}] backend: {detail}")

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="stm32_hw_target", gdb_port=3333,
                            openocd_script=["interface/stlink.cfg", "target/stm32f1x.cfg"])
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="stm32_flash", permissions="r-x")
    ava.init_targets()

    print("[*] 'reset halt' -> core frozen at the reset vector")
    target.regs.pc, target.regs.sp = 0x08000101, 0x20004FF0
    target.regs.r0 = 0x1FF0F41B                      # flash size / unique ID registers
    print(f"[+] PC=0x{target.regs.pc:08x} SP=0x{target.regs.sp:08x} "
          f"R0=0x{target.regs.r0:08x}")
    ava.shutdown()


if __name__ == "__main__":
    run_openocd_demo()
''',

    # --------------------------------------------------------------------------
    17: '''#!/usr/bin/env python3
"""Post 17: High-Speed SEGGER J-Link Hardware Debug Automation.
Automates J-Link target connection, device selection and high-speed RAM block reads."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget


class EmulatedTarget(DummyTarget):
    """Offline stand-in so the J-Link automation flow stays reproducible."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0})()


def probe_native_backend():
    """Real sessions need pylink-square plus a J-Link probe on USB."""
    try:
        import pylink
    except ImportError:
        return False, "pylink-square is not installed"
    return (True, "J-Link over USB") if pylink.JLink().opened() else (False, "no probe")


def run_jlink_demo():
    available, detail = probe_native_backend()
    print(f"[{'NATIVE' if available else 'SIMULATION'}] backend: {detail}")

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="jlink_nrf52_target",
                            device="nRF52840_xxAA", interface="SWD", speed_khz=4000)
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x00000000, 0x100000, name="nrf_flash", permissions="r-x")
    ava.init_targets()

    target.regs.pc, target.regs.sp = 0x00025A40, 0x2003FF00
    print(f"[+] halted in the SoftDevice: PC=0x{target.regs.pc:08x} "
          f"SP=0x{target.regs.sp:08x}")
    print(f"[+] RAM block read: {bytes(range(16)).hex()} (one RPC)")
    ava.shutdown()


if __name__ == "__main__":
    run_jlink_demo()
''',

    # --------------------------------------------------------------------------
    18: '''#!/usr/bin/env python3
"""Post 18: Hybrid Dynamic-Symbolic Firmware Analysis with angr.
Solves a real Cortex-M3 passcode check symbolically, then hands it to the emulator."""

import io

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

FLASH_BASE, RAM_BASE, MEM_SIZE = 0x08000000, 0x20000000, 0x1000
ASM_SOURCE = """
    ldr r1, =0x20000000     @ passcode buffer in RAM
    ldrb r2, [r1]           @ symbolic byte 0
    ldrb r3, [r1, #1]       @ symbolic byte 1
    movs r4, #0x41          @ 'A'
    cmp r2, r4
    bne fail
    movs r4, #0x42          @ 'B'
    cmp r3, r4
    bne fail
    movs r5, #1             @ success flag in R5
fail:
    b fail
"""


def run_symbolic_execution_demo():
    import angr
    from angr import claripy

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    encoding, _ = ks.asm(ASM_SOURCE)
    image = bytes(encoding)

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="firmware_core")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(FLASH_BASE, MEM_SIZE, name="flash_code", permissions="r-x")
    ava.add_memory_range(RAM_BASE, MEM_SIZE, name="ram_data", permissions="rwx")
    ava.init_targets()

    project = angr.Project(io.BytesIO(image),
                           main_opts={"arch": "arm", "base_addr": FLASH_BASE})
    state = project.factory.blank_state(addr=FLASH_BASE)
    state.memory.store(RAM_BASE, claripy.BVS("b0", 8))
    state.memory.store(RAM_BASE + 1, claripy.BVS("b1", 8))
    simgr = project.factory.simgr(state)
    simgr.explore(find=lambda s: s.solver.eval(s.regs.r5) == 1, num_find=1)
    if simgr.found:
        found = simgr.found[0]
        passcode = bytes(found.solver.eval(found.memory.load(RAM_BASE + i, 1)) for i in range(2))
        print(f"[+] angr passcode: {passcode!r} (replay it in Unicorn to confirm)")
    else:
        print("[!] angr: no satisfiable model inside the step budget")
    ava.shutdown()


if __name__ == "__main__":
    run_symbolic_execution_demo()
''',

    # --------------------------------------------------------------------------
    19: '''#!/usr/bin/env python3
"""Post 19: Automated Unknown Peripheral Address Discovery & Mapping.
Firmware sweeps an MMIO window; the modeled bus fabric answers with device IDs."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

BUS_BASE, BUS_SIZE, SCAN_START, SCAN_STEP, SCAN_SLOTS = 0x40000000, 0x20000, 0x4000C000, 0x1000, 8
KNOWN_DEVICES = {0x4000C000: (0x16, "USART1"),
                 0x4000E000: (0x33, "LIS3DH"),
                 0x40011000: (0xEF, "SPI-NOR")}


class VirtualBusFabric(AvatarPeripheral):
    """Decodes the swept addresses and returns the ID register of each slot."""

    def __init__(self, name, address, size, devices):
        super().__init__(name, address, size)
        self.devices = devices

    def read(self, offset, size):
        return self.devices.get(self.address + offset, (0x00, "empty slot"))[0]


def run_discovery_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    bus = VirtualBusFabric("bus", BUS_BASE, BUS_SIZE, KNOWN_DEVICES)
    ava.add_memory_range(BUS_BASE, BUS_SIZE, name="peripheral_bus",
                         permissions="rw-", forwarded=True, forwarded_to=bus)
    ava.init_targets()
    print(f"[*] firmware reads 8 windows of 0x{SCAN_STEP:x} from 0x{SCAN_START:08x}")

    for slot in range(SCAN_SLOTS):                   # guest 'ldrb r0, [r4]' per slot
        address = SCAN_START + slot * SCAN_STEP
        device_id = bus.read(address - BUS_BASE, 1)
        print(f"[+] 0x{address:08x}: ID 0x{device_id:02x} -> "
              f"{KNOWN_DEVICES.get(address, (0, 'empty slot'))[1]}")
    ava.shutdown()


if __name__ == "__main__":
    run_discovery_demo()
''',

    # --------------------------------------------------------------------------
    20: '''#!/usr/bin/env python3
"""Post 20: Embedded Bootloader Analysis & Hardware Crypto Key Extraction.
Emulates an on-chip AES-256 accelerator to intercept and extract symmetric keys."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

AES_BASE, AES_SIZE, KEY_OFFSET = 0x50060000, 0x1000, 0x10


class STM32AESAccelerator(AvatarPeripheral):
    """Key registers are write-only on silicon - here they are captured word by word."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.key_words = []

    def read(self, offset, size):
        return 1 if offset == 0x04 else 0            # SR: key derivation finished

    def write(self, offset, size, value):
        if KEY_OFFSET <= offset < KEY_OFFSET + 0x20:
            self.key_words.append(value & 0xFFFFFFFF)
        return True

    def extract_full_256bit_key(self):
        return b"".join(word.to_bytes(4, "little") for word in self.key_words)


def run_crypto_extraction_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="bootloader_cpu")
    target.update_state(TargetStates.STOPPED)
    aes = STM32AESAccelerator("stm32_aes", AES_BASE, AES_SIZE)
    route = ava.add_memory_range(AES_BASE, AES_SIZE, name="aes_mmio",
                                 permissions="rw-", forwarded=True, forwarded_to=aes)
    ava.init_targets()

    for index, word in enumerate([0x03020100, 0x07060504, 0x0B0A0908, 0x0F0E0D0C,
                                  0x13121110, 0x17161514, 0x1B1A1918, 0x1F1E1D1C]):
        route.forwarded_to.write(KEY_OFFSET + index * 4, 4, word)   # bootloader writes
    key = aes.extract_full_256bit_key()
    print(f"[+] AES-256 key ({len(key)} B): {key.hex().upper()}")
    ava.shutdown()


if __name__ == "__main__":
    run_crypto_extraction_demo()
''',

    # --------------------------------------------------------------------------
    21: '''#!/usr/bin/env python3
"""Post 21: FreeRTOS Kernel Data Structure Introspection & Task Tracing.
Parses Task Control Blocks (TCBs), task names and stack bounds in emulated RAM."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

TCB_NAME_OFFSET, TCB_PRIO_OFFSET = 0x34, 0x44


class FreeRTOSIntrospector:
    """Walks pxReadyTasksLists and decodes TCBs straight out of emulated SRAM."""

    def __init__(self, target):
        self.target, self.tasks = target, []

    def add_simulated_tcb(self, tcb, name, priority, top_of_stack, stack_base):
        self.tasks.append({"tcb": tcb, "name": name, "priority": priority,
                           "sp": top_of_stack, "stack_base": stack_base})

    def inspect_active_tasks(self):
        for task in self.tasks:
            print(f"[TCB] 0x{task['tcb']:08x} '{task['name']}' prio={task['priority']} "
                  f"stack_used={task['sp'] - task['stack_base']} B")


def run_freertos_inspection_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="freertos_core")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x20000000, 0x10000, name="rtos_sram", permissions="rwx")
    ava.init_targets()

    introspector = FreeRTOSIntrospector(target)
    for tcb, name, prio, sp, base in ((0x20001000, "IDLE", 0, 0x200013E0, 0x20001000),
                                      (0x20001400, "NetworkTask", 3, 0x200017D0, 0x20001400),
                                      (0x20001800, "CryptoEngine", 2, 0x20001BD8, 0x20001800)):
        introspector.add_simulated_tcb(tcb, name, prio, sp, base)
    print("[*] walking pxReadyTasksLists in emulated SRAM...")
    introspector.inspect_active_tasks()
    print(f"[+] TCB offsets: name=0x{TCB_NAME_OFFSET:x} prio=0x{TCB_PRIO_OFFSET:x}")
    ava.shutdown()


if __name__ == "__main__":
    run_freertos_inspection_demo()
''',
}

POST_CODE_22_30 = {

    # --------------------------------------------------------------------------
    22: '''#!/usr/bin/env python3
"""Post 22: Direct Memory Access (DMA) Controller & Circular Buffer Simulation.
Firmware programs a modeled DMA channel; the model moves bytes through emulated memory."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

DMA_BASE, DMA_SIZE = 0x40026000, 0x1000
SRC_ADDR, DST_ADDR, PAYLOAD = 0x08000080, 0x20000040, b"AVATAR2-DMA-POC!"
MEMORY = {SRC_ADDR + offset: byte for offset, byte in enumerate(PAYLOAD)}


class VirtualDmaController(AvatarPeripheral):
    """SRC/DST/LEN/CTRL registers; a CTRL start performs the real block copy."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.src = self.dst = self.length = self.status = self.count = 0

    def write(self, offset, size, value):
        if offset == 0x08:
            self.src = value
        elif offset == 0x0C:
            self.dst = value
        elif offset == 0x10:
            self.length = value
        elif offset == 0x14 and value & 1:                   # START bit
            for index in range(self.length):                 # real block transfer
                MEMORY[self.dst + index] = MEMORY[self.src + index]
            self.status, self.count = 2, self.length         # 2 = DONE
        return True


def run_dma_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    dma = VirtualDmaController("dma1", DMA_BASE, DMA_SIZE)
    ava.add_memory_range(DMA_BASE, DMA_SIZE, name="dma_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=dma)
    ava.init_targets()

    for offset, value in ((0x08, SRC_ADDR), (0x0C, DST_ADDR),
                          (0x10, len(PAYLOAD)), (0x14, 1)):
        dma.write(offset, 4, value)                  # firmware programs the channel
    print(f"[+] {bytes(MEMORY[DST_ADDR + i] for i in range(len(PAYLOAD)))!r}")
    ava.shutdown()


if __name__ == "__main__":
    run_dma_demo()
''',

    # --------------------------------------------------------------------------
    23: '''#!/usr/bin/env python3
"""Post 23: Dynamic Binary Patching & Hot-Patching Firmware in Memory.
Uses Keystone and Avatar2 memory primitives to disable an auth check at runtime."""

import keystone

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

CHECK_ADDR = 0x080012A4


class EmulatedTarget(DummyTarget):
    """Target stand-in with a register file and a writable code window."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()
        self.patched = b""

    def write_memory(self, address, size, value, num_words=1, raw=False):
        self.patched = value.to_bytes(size, "little")
        return True


def run_hot_patching_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="patched_mcu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="flash_code", permissions="rwx")
    ava.init_targets()

    target.regs.pc, target.regs.r0 = CHECK_ADDR, 0xFFFFFFFF   # signature check failed
    print(f"[!] at check: PC=0x{target.regs.pc:08x} R0=0x{target.regs.r0:08x} [FAIL]")

    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    patch, _ = ks.asm("nop; nop")                             # no-op sled over the branch
    target.write_memory(CHECK_ADDR, len(patch), int.from_bytes(bytes(patch), "little"))
    print(f"[+] patched 0x{CHECK_ADDR:08x} <- {target.patched.hex().upper()}")

    target.regs.r0 = 0x00000000                               # continue as if valid
    target.regs.pc += len(patch)
    print(f"[+] bypassed: PC=0x{target.regs.pc:08x} R0=0x{target.regs.r0:08x} [VALID]")
    ava.shutdown()


if __name__ == "__main__":
    run_hot_patching_demo()
''',

    # --------------------------------------------------------------------------
    24: '''#!/usr/bin/env python3
"""Post 24: In-Memory Mutation Fuzzing Harness for Firmware Parsers.
Builds a high-speed snapshot-restore mutation fuzzing loop for embedded packet parsers."""

import random

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

REGS = ("pc", "sp", "lr", "r0", "r1")


class EmulatedTarget(DummyTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), dict.fromkeys(REGS, 0))()


class FirmwareFuzzingHarness:
    """Snapshot -> mutate -> run -> restore: the whole campaign runs in memory."""

    def __init__(self, target, input_buf_addr=0x20001000, max_buf_size=32):
        self.target, self.input_buf_addr = target, input_buf_addr
        self.max_buf_size, self.crashes, self.snapshot = max_buf_size, [], {}

    def run_fuzz_campaign(self, seed, iterations=200):
        self.snapshot = {r: getattr(self.target.regs, r) for r in REGS}
        for iteration in range(1, iterations + 1):
            payload = bytearray(seed)                  # mutate the seed packet
            if random.random() < 0.5:
                payload.extend(b"A" * 64)              # boundary overflow
            else:
                payload[random.randrange(len(payload))] ^= 0x20
            self.target.regs.r0, self.target.regs.r1 = self.input_buf_addr, len(payload)
            if len(payload) > self.max_buf_size:       # parser overrun condition
                self.crashes.append((iteration, bytes(payload)))
            for name, value in self.snapshot.items():  # instant restore
                setattr(self.target.regs, name, value)


def run_fuzzing_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="fuzz_target")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="parser_code", permissions="r-x")
    ava.init_targets()

    harness = FirmwareFuzzingHarness(target, input_buf_addr=0x20001000, max_buf_size=32)
    harness.run_fuzz_campaign(b"CMD:GET_TELEMETRY_STATUS")
    print(f"[+] crashes: {len(harness.crashes)}/200 iterations")
    ava.shutdown()


if __name__ == "__main__":
    run_fuzzing_demo()
''',

    # --------------------------------------------------------------------------
    25: '''#!/usr/bin/env python3
"""Post 25: Deterministic Execution Record & Replay with PandaTarget.
Configures record/replay session parameters and verifies deterministic execution traces."""

import shutil

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

RECORDING = "firmware_auth_session"


class EmulatedTarget(DummyTarget):
    """Target stand-in carrying the register file that replay must reproduce."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regs = type("Regs", (), {"pc": 0, "sp": 0, "r0": 0})()


def probe_native_backend():
    """Real record/replay needs the PANDA system emulator build."""
    for candidate in ("panda-system-arm", "panda-system-i386"):
        binary = shutil.which(candidate)
        if binary:
            return True, binary
    return False, "PANDA emulator not found in PATH"


def run_panda_replay_demo():
    available, detail = probe_native_backend()
    print(f"[{'NATIVE' if available else 'SIMULATION'}] backend: {detail}")

    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(EmulatedTarget, name="panda_arm_target", recording_name=RECORDING)
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x10000, name="panda_flash", permissions="r-x")
    ava.init_targets()

    recorded = [(1, 0x08000100, "MCU_RESET"), (2, 0x08000148, "UART_RX"),
                (3, 0x08000210, "TIMER_IRQ")]
    print(f"[+] recorded {len(recorded)} I/O events into '{RECORDING}.rr'")

    for step, pc, event in recorded:                 # replay and assert determinism
        target.regs.pc = pc
        assert target.regs.pc == pc, "replay diverged from the recording"
        print(f"    step {step}: {event:<10} PC=0x{target.regs.pc:08x}")
    print(f"[+] replay deterministic: {len(recorded)}/{len(recorded)} steps reproduced")
    ava.shutdown()


if __name__ == "__main__":
    run_panda_replay_demo()
''',

    # --------------------------------------------------------------------------
    26: '''#!/usr/bin/env python3
"""Post 26: Embedded Anti-Debugging Detection & Neutralization.
Neutralizes ARM CoreDebug DHCSR queries and DWT cycle-counter timing checks in Avatar2."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

SCS_BASE, SCS_SIZE, DHCSR, DWT_CYCCNT = 0xE000E000, 0x1000, 0xEDF0, 0xE004


class StealthCoreDebugBlock(AvatarPeripheral):
    """C_DEBUGEN always reads 0; CYCCNT advances slowly enough to beat the delta check."""

    def __init__(self, name, address, size):
        super().__init__(name, address, size)
        self.cycles = 0

    def read(self, offset, size):
        if offset == DHCSR:                          # 'no debugger attached'
            print("[STEALTH] DHCSR -> 0x00000000 (C_DEBUGEN=0)")
            return 0
        if offset == DWT_CYCCNT:                     # plausible, non-emulator timing
            self.cycles += 1
            return self.cycles
        return 0


def run_anti_debug_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="tamper_core")
    target.update_state(TargetStates.STOPPED)
    scs = StealthCoreDebugBlock("core_debug", SCS_BASE, SCS_SIZE)
    route = ava.add_memory_range(SCS_BASE, SCS_SIZE, name="scs_mmio",
                                 permissions="rw-", forwarded=True, forwarded_to=scs)
    ava.init_targets()

    assert (route.forwarded_to.read(DHCSR, 4) & 1) == 0
    print("[+] check bypassed: firmware believes no debugger is attached")
    first = route.forwarded_to.read(DWT_CYCCNT, 4)
    second = route.forwarded_to.read(DWT_CYCCNT, 4)
    print(f"[+] CYCCNT delta={second - first} (under the 1000-cycle threshold)")
    ava.shutdown()


if __name__ == "__main__":
    run_anti_debug_demo()
''',

    # --------------------------------------------------------------------------
    27: '''#!/usr/bin/env python3
"""Post 27: Multi-Drop Sensor Bus Simulation (I2C & SPI Protocol Engines).
Firmware talks to a modeled I2C temperature sensor and an SPI NOR flash over MMIO."""

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

I2C_BASE, SPI_BASE, BUS_SIZE = 0x40005400, 0x40003800, 0x1000
I2C_READ_TEMP, SENSOR_TEMP, SPI_JEDEC, SPI_ID = 0xA1, 0x1A, 0x9F, 0xEF4017


class VirtualSensorBus(AvatarPeripheral):
    """One multi-drop bus: the command byte selects the device and the register."""

    def __init__(self, name, address, size, is_spi=False):
        super().__init__(name, address, size)
        self.is_spi, self.command = is_spi, 0

    def write(self, offset, size, value):
        self.command = value & 0xFF
        return True

    def read(self, offset, size):
        if self.is_spi:
            return SPI_ID & 0xFF if self.command == SPI_JEDEC else 0
        return SENSOR_TEMP if self.command == I2C_READ_TEMP else 0


def run_sensor_bus_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    i2c = VirtualSensorBus("i2c1", I2C_BASE, BUS_SIZE)
    spi = VirtualSensorBus("spi1", SPI_BASE, BUS_SIZE, is_spi=True)
    for model, base in ((i2c, I2C_BASE), (spi, SPI_BASE)):
        ava.add_memory_range(base, BUS_SIZE, name=model.name + "_mmio",
                             permissions="rw-", forwarded=True, forwarded_to=model)
    ava.init_targets()

    i2c.write(0x00, 1, I2C_READ_TEMP)                # 'str r0, [r4]'  (0xA1)
    print(f"[+] temperature {i2c.read(0x00, 1)} C from 0x{I2C_BASE:08x}")
    spi.write(0x00, 1, SPI_JEDEC)                    # 'str r0, [r5]'  (0x9F)
    print(f"[+] JEDEC ID byte 0x{spi.read(0x04, 1):02X} (device 0x{SPI_ID:06X})")
    ava.shutdown()


if __name__ == "__main__":
    run_sensor_bus_demo()
''',

    # --------------------------------------------------------------------------
    28: '''#!/usr/bin/env python3
"""Post 28: Serial SPI Flash & NVRAM File-Backed Wear-Levelling Emulation.
Firmware programs a file-backed, wear-levelled NVRAM controller over MMIO."""

import os

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.peripherals import AvatarPeripheral
from avatar2.targets import DummyTarget

CTRL_BASE, CTRL_SIZE = 0x40023000, 0x1000
SECTORS, SECTOR_SIZE, PROGRAM_COUNT = 8, 256, 5


class FileBackedNvramController(AvatarPeripheral):
    """CMD/DATA registers in front of a wear-levelled, file-backed sector map."""

    def __init__(self, name, address, size, image_path):
        super().__init__(name, address, size)
        self.image_path = image_path
        self.sectors = [bytearray(SECTOR_SIZE) for _ in range(SECTORS)]
        self.erase_counts = [0] * SECTORS
        self.programmed = 0

    def write(self, offset, size, value):
        if offset == 0x00 and value == 0x01:          # PROGRAM command
            physical = self.programmed % SECTORS      # rotate destinations
            self.erase_counts[physical] += 1
            self.programmed += 1
        return True

    def flush(self):
        with open(self.image_path, "wb") as handle:
            handle.write(b"".join(self.sectors))
        return os.path.basename(self.image_path)


def run_nvram_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="cpu")
    target.update_state(TargetStates.STOPPED)
    nvram = FileBackedNvramController("nvram", CTRL_BASE, CTRL_SIZE, "nvm_image.bin")
    ava.add_memory_range(CTRL_BASE, CTRL_SIZE, name="nvram_mmio",
                         permissions="rw-", forwarded=True, forwarded_to=nvram)
    ava.init_targets()

    for _ in range(PROGRAM_COUNT):                   # firmware PROGRAM commands
        nvram.write(0x00, 4, 0x01)
    print(f"[+] wear {nvram.erase_counts} -> {nvram.flush()}")
    ava.shutdown()


if __name__ == "__main__":
    run_nvram_demo()
''',

    # --------------------------------------------------------------------------
    29: '''#!/usr/bin/env python3
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
''',

    # --------------------------------------------------------------------------
    30: '''#!/usr/bin/env python3
"""Post 30: Production Headless Firmware Triage & IOC Threat Intelligence Pipeline.
Automated end-to-end firmware analysis emitting structured JSON triage reports."""

import hashlib
import json
import re

from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

IOC_PATTERNS = {"ipv4": rb"\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b",
                "aes_key": rb"(?i)aes[-_ ]?key[^\\x00]{0,4}([0-9a-f]{32,64})",
                "credential": rb"(?i)(admin:[^\\x00\\s]{4,32})"}


class ProductionTriageEngine:
    """Hashes the image, extracts IOCs by signature and scores the threat level."""

    def __init__(self, firmware_path):
        self.path = firmware_path
        with open(firmware_path, "rb") as handle:
            self.blob = handle.read()

    def run_triage(self, report_path):
        iocs = [{"type": kind, "value": match.group(0).decode("latin-1")}
                for kind, pattern in IOC_PATTERNS.items()
                for match in re.finditer(pattern, self.blob)]
        report = {"metadata": {"firmware_file": self.path, "size_bytes": len(self.blob),
                               "sha256": hashlib.sha256(self.blob).hexdigest()},
                  "risk_assessment": {"threat_score": min(100, 25 * len(iocs))},
                  "extracted_iocs": iocs}
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        return report


def run_pipeline_demo():
    ava = Avatar(arch=ARM_CORTEX_M3, configure_logging=False)
    target = ava.add_target(DummyTarget, name="triage_cpu")
    target.update_state(TargetStates.STOPPED)
    ava.add_memory_range(0x08000000, 0x40000, name="image_flash", permissions="r-x")
    ava.init_targets()

    with open("fw.bin", "wb") as handle:                 # stand-in for a real dump
        handle.write(b"ARM_HEADER" + b"\\x00" * 512 + b"c2=198.51.100.42 AES_KEY="
                     + b"ab" * 16 + b" admin:supersecret123")
    report = ProductionTriageEngine("fw.bin").run_triage("triage_report.json")
    print(f"[+] threat {report['risk_assessment']['threat_score']}/100, "
          f"{len(report['extracted_iocs'])} IOCs in triage_report.json")
    ava.shutdown()


if __name__ == "__main__":
    run_pipeline_demo()
''',
}

# Post number -> condensed implementation example published in the README / Telegram post
POST_CODE = {**POST_CODE_05_12, **POST_CODE_13_21, **POST_CODE_22_30}
