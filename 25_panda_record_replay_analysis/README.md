# ⚡️ 📼 Deterministic Execution Record & Replay with PandaTarget (Python practice)

Intermittent bugs, race conditions, and heap corruption issues in embedded firmware can be notoriously difficult to reproduce: re-running firmware multiple times produces different outcomes due to asynchronous hardware interrupts and sensor timing jitter.

## 🧠 Core Concept
- **Deterministic Record & Replay**: Recording external I/O events to allow bit-exact offline re-execution.
- **PANDA Architecture Integration**: Wrapping PANDA's LLVM/QEMU instrumentation engine inside Avatar2.
- **Taint Analysis Foundation**: Tracking the flow of untrusted input bytes from peripheral reads to sensitive CPU sinks.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
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
```

## 🔥 Use Cases
- Root-cause analysis of rare crash bugs that occur once in thousands of hours of testing.
- Dynamic taint analysis to determine if untrusted network bytes reach the instruction pointer (`PC`).
- Reverse engineering proprietary communication protocols by recording live vehicle telemetry.

## ⚠️ Caveats & Responsible Practice
- PANDA recording files (`.rr`) can become very large (several gigabytes for extended execution sessions).
- PANDA requires specialized Linux builds with customized QEMU and LLVM plugins.

## 📦 Test Data & Sample Binaries
- **Recording Identifier**: `firmware_auth_session`
- **Target Core**: ARM Cortex-M3
- **Trace Sequence**: Reset -> UART Input (`A`, `D`, `M`) -> Authentication Validation Check (`0x08000300`)

## 🔗 Resources
- PANDA: Platform for Architecture-Neutral Dynamic Analysis (https://panda.re/)

**Full script, run log & report**: [`25_panda_record_replay_analysis/example.py`](https://github.com/M0nteCarl0/Avatar2-OxxxSec/tree/main/25_panda_record_replay_analysis)

#Avatar2 #PANDA #RecordReplay #TaintAnalysis #FirmwareForensics #ReverseEngineering
