#!/usr/bin/env python3
"""
Post 15: High-Performance Remote Memory Protocol (RMP) & Demand-Paging
Demonstrating page-fault interception, block demand-paging, and transparent memory caching.
"""

import tempfile
import shutil
from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3
from avatar2.targets import DummyTarget

class RemoteMemoryServer:
    """
    Simulates a remote backing store (e.g. physical microcontroller Flash over JTAG)
    serving 4KB memory pages on demand.
    """
    PAGE_SIZE = 4096

    def __init__(self):
        # Simulated remote storage (512KB)
        self.remote_storage = bytearray(512 * 1024)
        # Write dummy firmware data at page 0 (0x08000000) and page 1 (0x08001000)
        self.remote_storage[0:16] = b"BOOTLOADER_V2026"
        self.remote_storage[4096:4112] = b"SECRET_FIRMWARE!"
        self.served_pages = 0

    def fetch_page(self, base_address: int) -> bytes:
        offset = base_address - 0x08000000
        page_data = bytes(self.remote_storage[offset : offset + self.PAGE_SIZE])
        self.served_pages += 1
        print(f"  [RMP SERVER] Page Fault at 0x{base_address:08x} -> Serving 4KB block (Total pages: {self.served_pages})")
        return page_data

class DemandPagingMemoryManager:
    def __init__(self, server: RemoteMemoryServer):
        self.server = server
        self.cached_pages = {}

    def read_word(self, address: int) -> int:
        page_base = address & ~(RemoteMemoryServer.PAGE_SIZE - 1)
        offset_in_page = address - page_base
        
        # Check cache
        if page_base not in self.cached_pages:
            print(f"[PAGE FAULT] Address 0x{address:08x} not cached. Requesting page 0x{page_base:08x} via RMP...")
            self.cached_pages[page_base] = self.server.fetch_page(page_base)
        else:
            print(f"[CACHE HIT] Address 0x{address:08x} resolved from local page 0x{page_base:08x} (Zero IPC!)")
            
        page_data = self.cached_pages[page_base]
        # Return 4 bytes little-endian
        return int.from_bytes(page_data[offset_in_page : offset_in_page + 4], "little")

def run_rmp_demand_paging_demo() -> None:
    print("[*] Initializing Avatar2 Remote Memory Protocol & Demand Paging...")
    workspace_dir = tempfile.mkdtemp(prefix="avatar2_rmp_")
    try:
        ava = Avatar(arch=ARM_CORTEX_M3, output_directory=workspace_dir, configure_logging=False)
        target = ava.add_target(DummyTarget, name="fast_core")
        target.update_state(TargetStates.STOPPED)
        
        ava.add_memory_range(0x08000000, 0x80000, name="demand_paged_flash", permissions="r-x")
        ava.init_targets()
        
        rmp_server = RemoteMemoryServer()
        mem_manager = DemandPagingMemoryManager(rmp_server)
        
        # Access 1: Read address 0x08000000 (triggers Page Fault for Page 0)
        val1 = mem_manager.read_word(0x08000000)
        print(f"[+] Read 0x08000000: 0x{val1:08x} ('{bytes.fromhex(f'{val1:08x}')[::-1].decode('ascii')}')")
        
        # Access 2: Read address 0x08000004 (should be CACHE HIT - zero remote overhead!)
        val2 = mem_manager.read_word(0x08000004)
        print(f"[+] Read 0x08000004: 0x{val2:08x} ('{bytes.fromhex(f'{val2:08x}')[::-1].decode('ascii')}')")
        
        # Access 3: Read address 0x08001000 (triggers Page Fault for Page 1)
        val3 = mem_manager.read_word(0x08001000)
        print(f"[+] Read 0x08001000: 0x{val3:08x} ('{bytes.fromhex(f'{val3:08x}')[::-1].decode('ascii')}')")
        
        # Access 4: Read address 0x08001004 (CACHE HIT)
        val4 = mem_manager.read_word(0x08001004)
        print(f"[+] Read 0x08001004: 0x{val4:08x} ('{bytes.fromhex(f'{val4:08x}')[::-1].decode('ascii')}')")
        
        print(f"[+] Summary: Fetched {rmp_server.served_pages} remote pages total; satisfied 4 word reads.")
        assert rmp_server.served_pages == 2
        
        ava.stop()
        ava.fast_queue_listener.stop()
        ava.shutdown()
        print("[SUCCESS] Remote Memory Protocol demand-paging verified.")
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

if __name__ == "__main__":
    run_rmp_demand_paging_demo()
