import random
import os
from physical_file import PhysicalFile
from mmu import MMU

if __name__ == "__main__":
    # Create sample native files
    sample_files = ["inventory.db", "video_meta.dat", "app_logs.txt"]
    for fname in sample_files:
        if not os.path.exists(fname):
            with open(fname, "wb") as f:
                f.write(b"Real native file data for MMU simulation.\n" * 1500)

    mmu = MMU()
    files = [PhysicalFile(f) for f in sample_files]

    print("MMU Simulation Started...\n")

    for i in range(300):
        p_file = random.choice(files)
        page = random.randint(0, min(200, p_file.num_pages - 1))
        is_write = random.random() < 0.25

        data = b"Updated data" if is_write else None
        mmu.access(p_file, page, data)

        if i % 80 == 0:
            print(f"Access {i:3d} | Faults: {mmu.stats['faults']:3d} | Hits: {mmu.stats['hits']:3d}")

    # Final Dump
    mmu.dump()

    print("\nSimulation completed. Check output.log for full details.")