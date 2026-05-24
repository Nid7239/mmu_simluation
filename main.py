import random
import os
from physical_file import PhysicalFile
from mmu import MMU

if __name__ == "__main__":
    sample_files = ["inventory.db", "video_meta.dat", "app_logs.txt"]
    
    # Create sample native files
    for fname in sample_files:
        if not os.path.exists(fname):
            with open(fname, "wb") as f:
                f.write(b"Sample native file data for MMU simulation.\n" * 800)

    mmu = MMU()
    files = [PhysicalFile(f) for f in sample_files]

    TOTAL_ACCESSES = 120

    print(f"MMU Simulation Started with {TOTAL_ACCESSES} accesses...\n")

    for i in range(TOTAL_ACCESSES):
        p_file = random.choice(files)
        page = random.randint(0, min(200, p_file.num_pages - 1))
        is_write = random.random() < 0.3

        data = b"Updated data" if is_write else None
        mmu.access(p_file, page, data)

        if i % 30 == 0:
            print(f"Access {i:3d} | Faults: {mmu.stats['faults']:3d} | Hits: {mmu.stats['hits']:3d}")

    mmu.dump()
    print(f"\nSimulation completed. Check output.log for detailed tables.")