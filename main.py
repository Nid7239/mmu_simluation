"""
main.py
=======
Simulation driver for the MMU.

Creates three sample files, runs 120 random page accesses (30 % writes),
and prints periodic progress to the console.

Output files
------------
  output.log : High-level summary — frame table, page directory, TLB
               state, and statistics at the end of the simulation.
  trace.log  : Step-by-step internal trace — every access showing the
               VPN bit-split, TLB/page-table lookup result, evictions,
               writebacks, and a full frame snapshot after each step.
"""

from __future__ import annotations
import os
import random

from physical_file import PhysicalFile
from mmu import MMU


SAMPLE_FILES   = ["inventory.db", "video_meta.dat", "app_logs.txt"]
TOTAL_ACCESSES = 10
WRITE_RATIO    = 0.30
PROGRESS_EVERY =5


def _ensure_sample_files() -> None:
    """Create sample files on disk if they do not already exist."""
    for fname in SAMPLE_FILES:
        if not os.path.exists(fname):
            with open(fname, "wb") as fh:
                fh.write(b"Sample data for MMU simulation.\n" * 800)


def main() -> None:
    _ensure_sample_files()

    mmu = MMU(trace=True)          # trace=True → also writes trace.log
    files = [PhysicalFile(f) for f in SAMPLE_FILES]

    print(
        f"MMU Simulation — {TOTAL_ACCESSES} accesses across {len(files)} file(s)\n"
    )

    for i in range(TOTAL_ACCESSES):
        p_file     = random.choice(files)
        vpn        = random.randint(0, min(8, p_file.num_pages - 1))
        is_write   = random.random() < WRITE_RATIO
        write_data = (b"Updated data " * 5)[:64] if is_write else None

        mmu.access(p_file, vpn, write_data)

        if i % PROGRESS_EVERY == 0:
            print(
                f"  Access {i:>3}  |  Faults: {mmu.stats['faults']:>3}  "
                f"Hits: {mmu.stats['hits']:>3}  "
                f"TLB hits: {mmu.stats['tlb_hits']:>3}"
            )

    mmu.dump()
    mmu.close()
    print("Simulation complete.")
    print("  Summary  → output.log")
    print("  Trace    → trace.log")


if __name__ == "__main__":
    main()