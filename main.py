# main.py
import os
import sys
import time
from physical_file import PhysicalFile
from mmu import MMU

def print_trace_header(access_num: int, filename: str, page: int, mode: str):
    print("\n" + "="*95)
    print(f" ACCESS #{access_num:<3} | File: {filename:<15} | Page: {page:<4} | Mode: {mode}")
    print("="*95)

if __name__ == "__main__":
    log_file_path = "output.log"
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    
    try:
        # Initialize our virtual MMU device engine with 5 open frame records
        mmu = MMU(num_frames=5)
        
        # Instantiate 5 separate mock native input/output files
        logs   = PhysicalFile("app_logs.txt")
        db     = PhysicalFile("user_db.bin")
        cfg    = PhysicalFile("config.json")
        cache  = PhysicalFile("cache.dat")
        report = PhysicalFile("report.pdf")

        # Access 1 -> Frame 0
        print_trace_header(1, logs.file_id, 0, "READ")
        mmu.access(logs, 0, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 2 -> Frame 1
        print_trace_header(2, db.file_id, 0, "READ")
        mmu.access(db, 0, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 3 -> Frame 2
        print_trace_header(3, cfg.file_id, 1, "READ")
        mmu.access(cfg, 1, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 4 -> Frame 3
        print_trace_header(4, cache.file_id, 0, "READ")
        mmu.access(cache, 0, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 5 -> Frame 4 (Memory capacity matches 100%)
        print_trace_header(5, report.file_id, 2, "READ")
        mmu.access(report, 2, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 6 -> Triggers a Page Hit (Refreshes LRU tracking properties for logs)
        print_trace_header(6, logs.file_id, 0, "READ")
        mmu.access(logs, 0, "READ")
        time.sleep(0.01)
        mmu.dump()

        # Access 7 -> Triggers an LRU Eviction across separate file contexts
        print_trace_header(7, db.file_id, 3, "READ")
        mmu.access(db, 3, "READ")
        mmu.dump()

    finally:
        output_file = sys.stdout
        sys.stdout = sys.__stdout__  
        output_file.close()
        
        print(f"\n[SUCCESS] Multi-file native simulation run finalized!")
        print(f"The clean visual execution charts are saved in: {os.path.abspath(log_file_path)}\n")