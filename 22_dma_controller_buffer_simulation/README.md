# ⚡️ 🌊 Direct Memory Access (DMA) Controller & Circular Buffer Simulation (Python practice)

Direct Memory Access (DMA) controllers allow embedded microcontrollers to stream data between peripherals (ADC, SPI, UART, Ethernet) and internal SRAM in the background without CPU intervention.

## 🧠 Core Concept
- **DMA Architecture**: Channel configuration registers (`CCR`), transfer counters (`CNDTR`), source and destination addresses.
- **Asynchronous Background Copy**: Moving byte blocks from peripheral data registers into SRAM without CPU cycles.
- **Circular Mode Emulation**: Automatically reloading destination pointers when circular buffer wrapping occurs.

## 💻 Implementation Example
```python
#!/usr/bin/env python3
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
```

## 🔥 Use Cases
- Fuzzing network stack packet handlers fed exclusively through DMA Ethernet/UART buffers.
- Analyzing Time-of-Check to Time-of-Use (TOCTOU) race conditions in DMA memory regions.

## ⚠️ Caveats & Responsible Practice
- DMA transfers occur asynchronously; ensure memory barriers (`DSB`, `ISB`) are respected in analysis models.
- In physical Cortex-M7 systems with D-Cache, DMA transfers can cause cache incoherency bugs.

## 📦 Test Data & Sample Binaries
- **DMA Peripheral Model**: STM32 DMA1 Channel 1
- **Base Address**: `0x40020000` (Size: 4 KB)
- **Source Address**: `0x4000C000` (UART DR) | **Dest Address**: `0x20002000` (SRAM)

## 🔗 Resources
- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)
- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)
- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)
- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and dynamic-analysis playbook — this chapter's sources, run log, report and execution screenshot.

#Avatar2 #DMA #MemoryArchitecture #FirmwareSecurity #HardwareEmulation #Embedded
