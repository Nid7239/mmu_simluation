import os
from datetime import datetime
from file import PhysicalFile
from mmu import MMU
from constants import NUM_FRAMES, PAGE_SIZE


def run():
    mmu = MMU(NUM_FRAMES)

    f1 = PhysicalFile("inventory.db",   num_pages=4)
    f2 = PhysicalFile("video_meta.dat", num_pages=6)
    f3 = PhysicalFile("app_logs.txt",   num_pages=3)

    # (file, page_idx, optional_write_data)
    access_list = [
        (f1, 0, None),
        (f1, 1, None),
        (f2, 0, None),
        (f2, 1, None),
        (f1, 0, None),              # TLB_HIT  — f1/p0 in TLB
        (f3, 0, None),              # FAULT    — evicts LRU
        (f1, 1, None),              # FAULT    — f1/p1 was evicted
        (f3, 0, b"PATCHED___"),     # TLB_HIT  — write, marks dirty
        (f1, 0, None),              # TLB_HIT  — still in TLB
        (f2, 0, None),              # HIT/FAULT
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
        log.write("  " + "MMU SIMULATION  —  FULL ACCESS LOG".center(W) + "\n")
        log.write("  " + f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(W) + "\n")
        log.write("  " + "═" * W + "\n")

        log.write("\n  [ FILES GENERATED VIA os.urandom() ]\n")
        for f in (f1, f2, f3):
            log.write(f"  {'─'*W}\n")
            log.write(f"  File : {f.file_id}  |  {f.size} bytes  |  {f.num_pages} pages  (PAGE_SIZE={PAGE_SIZE})\n")
            for p in range(f.num_pages):
                log.write(f"    P{p}  →  {f.read_page(p).hex(' ')}\n")
        log.write(f"  {'─'*W}\n\n")

        for n, (fobj, p_idx, wdata) in enumerate(access_list, 1):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            status, data = mmu.access(fobj, p_idx, write_data=wdata)

            log.write(access_banner(n, fobj, p_idx, wdata) + "\n")
            log.write(f"  Timestamp : {ts}\n")
            log.write(f"  Result    : {status}\n")
            log.write(f"  Data      : {data.hex(' ')}\n")
            if wdata:
                log.write(f"  Written   : {wdata}\n")
            log.write(mmu.dump_state(accessed_file_id=fobj.file_id))

        log.write(f"\n  {'═'*W}\n")
        log.write("  SIMULATION COMPLETE\n")
        log.write(f"  {'═'*W}\n")
        log.write(mmu.dump_state())

    print("Done — see output.log")


if __name__ == "__main__":
    run()
