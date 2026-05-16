import os
from datetime import datetime
from file import PhysicalFile
from mmu import MMU
from constants import NUM_FRAMES, PAGE_SIZE


def run():
    # Initialize the MMU with our physical frame capacity
    mmu = MMU(NUM_FRAMES)

    # Instantiate our sample project files
    f1 = PhysicalFile("inventory.db",   num_pages=4)
    f2 = PhysicalFile("video_meta.dat", num_pages=6)
    f3 = PhysicalFile("app_logs.txt",   num_pages=3)

    # Simulation Access Steps: (file_object, page_index, optional_write_data)
    access_list = [
        (f1, 0, None),              # FAULT -> Allocates F0
        (f1, 1, None),              # FAULT -> Allocates F1
        (f2, 0, None),              # FAULT -> Allocates F2
        (f2, 1, None),              # FAULT -> Allocates F3 (RAM is now full)
        (f1, 0, None),              # TLB_HIT -> Reads f1 P0 out of cache
        (f3, 0, None),              # FAULT -> RAM full! Evicts LRU (f1 P1 from F1)
        (f1, 1, None),              # FAULT -> f1 P1 was evicted earlier, re-fetches it
        (f3, 0, b"PATCHED___"),     # TLB_HIT -> WRITE operation, sets DIRTY status
        (f1, 0, None),              # TLB_HIT -> Simple read hit
        (f2, 0, None),              # HIT -> Page table lookup hit
    ]

    W = 80

    def access_banner(n, fobj, p_idx, wdata):
        op = "WRITE" if wdata else "READ"
        return (
            f"\n  {'═'*W}\n"
            f"  ACCESS #{n:02d}  |  {op}  |  File: {fobj.file_id}  |  Page: P{p_idx}\n"
            f"  {'═'*W}"
        )

    with open("output.log", "w", encoding="utf-8") as log:
        log.write("  " + "═" * W + "\n")
        log.write("  " + "MMU SIMULATION  —  2-LEVEL HIERARCHICAL ACCESS LOG".center(W) + "\n")
        log.write("  " + f"Run Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(W) + "\n")
        log.write("  " + "═" * W + "\n")

        log.write("\n  [ TARGET FILE ARCHITECTURES ]\n")
        for f in (f1, f2, f3):
            log.write(f"  {'─'*W}\n")
            log.write(f"  File : {f.file_id:<16} | Size : {f.size:<3} bytes | Blocks : {f.num_pages} pages (PAGE_SIZE={PAGE_SIZE})\n")
        log.write(f"  {'─'*W}\n\n")

        # Execute the simulation operations loop
        for n, (fobj, p_idx, wdata) in enumerate(access_list, 1):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            status, data = mmu.access(fobj, p_idx, write_data=wdata)

            log.write(access_banner(n, fobj, p_idx, wdata) + "\n")
            log.write(f"  Timestamp : {ts}\n")
            log.write(f"  Result    : {status}\n")
            
            if wdata:
                # Decodes b'PATCHED___' into a clean clear-text format
                clean_string = wdata.decode("utf-8", errors="ignore")
                log.write(f"  Written   : {clean_string}\n")
                
            log.write(mmu.dump_state(accessed_file_id=fobj.file_id))

        log.write(f"\n  {'═'*W}\n")
        log.write("  SIMULATION RUN COMPLETE\n")
        log.write(f"  {'═'*W}\n")
        log.write(mmu.dump_state())

    print("Success — 2-Level Multi-Page Table execution logs saved to output.log")


if __name__ == "__main__":
    run()