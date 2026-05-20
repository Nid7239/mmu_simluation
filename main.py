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
        # Initialize MMU without arguments (it pulls from constants.py)
        mmu = MMU()
        
        logs   = PhysicalFile("app_logs.txt")
        db     = PhysicalFile("user_db.bin")
        cfg    = PhysicalFile("config.json")
        cache  = PhysicalFile("cache.dat")
        report = PhysicalFile("report.pdf")

        # Running the sequence
        accesses = [(logs, 0), (db, 0), (cfg, 1), (cache, 0), (report, 2), (logs, 0), (db, 3)]
        
        for i, (f, p) in enumerate(accesses, 1):
            print_trace_header(i, f.file_id, p, "READ")
            mmu.access(f, p, "READ")
            time.sleep(0.01)
            mmu.dump()

    finally:
        output_file = sys.stdout
        sys.stdout = sys.__stdout__  
        output_file.close()
        
        print(f"\n[SUCCESS] Simulation finalized! Logs in: {os.path.abspath(log_file_path)}")