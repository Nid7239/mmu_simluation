from datetime import datetime
import sys
from typing import Tuple
from frame import Frame
from page_directory import PageDirectory
from lru_bst import LRUBST
from physical_file import PhysicalFile
from constants import NUM_FRAMES, TLB_SIZE

class MMU:
    def __init__(self, num_frames: int = NUM_FRAMES):
        self.frames: list[Frame] = [Frame(i) for i in range(num_frames)]
        self.page_directory = PageDirectory()
        self.tlb: dict[Tuple[str, int], int] = {}
        self.lru = LRUBST()
        self.stats = {"hits": 0, "faults": 0, "tlb_hits": 0, "tlb_misses": 0, "writebacks": 0}

        # Redirect output to output.log
        self.log_file = open("output.log", "w", encoding="utf-8")
        sys.stdout = self.log_file

    def access(self, p_file: PhysicalFile, page_idx: int, write_data: bytes = None):
        key: Tuple[str, int] = (p_file.file_id, page_idx)
        now = datetime.now()

        # TLB Lookup
        if key in self.tlb:
            self.stats["tlb_hits"] += 1
            self.stats["hits"] += 1
            frame_idx = self.tlb[key]
        else:
            self.stats["tlb_misses"] += 1
            # Use table_idx to select which Page Table to use
            table_idx = page_idx // 32
            inner_idx = page_idx % 32

            entry = self.page_directory.get(table_idx, inner_idx)
            if entry:
                self.stats["hits"] += 1
                frame_idx = entry.frame_idx
                self.tlb[key] = frame_idx
            else:
                self.stats["faults"] += 1
                frame = self._evict_or_get_free()
                frame_idx = frame.idx

                frame.data = p_file.read_page(page_idx)
                frame.p_file = p_file
                frame.dirty = False

                self.page_directory.map(table_idx, inner_idx, frame_idx, now)
                self.tlb[key] = frame_idx

        # Update LRU with current timestamp
        self.lru.insert(key, now)

        frame = self.frames[frame_idx]
        if write_data:
            frame.data = write_data
            frame.dirty = True

        return frame.data

    def _evict_or_get_free(self) -> Frame:
        # Find free frame
        for frame in self.frames:
            if frame.p_file is None:
                return frame

        # LRU Eviction
        victim_key = self.lru.remove_oldest()
        if not victim_key:
            raise RuntimeError("No frames available")

        v_file, v_page = victim_key
        table_idx = v_page // 32
        inner_idx = v_page % 32

        entry = self.page_directory.get(table_idx, inner_idx)
        frame_idx = entry.frame_idx if entry else 0
        frame = self.frames[frame_idx]

        if frame.dirty and frame.p_file:
            self.stats["writebacks"] += 1
            frame.p_file.write_page(v_page, frame.data)

        self.tlb.pop(victim_key, None)
        self.page_directory.unmap(table_idx, inner_idx)
        frame.clear()

        return frame

    def dump(self):
        print("\n" + "="*90)
        print("MMU SIMULATION FINAL STATE")
        print("="*90)

        print("\n1. FRAME TABLE")
        print("-" * 70)
        print(f"{'Frame':<6} {'File ID':<20} {'Page':<8} {'Dirty':<6} Status")
        print("-" * 70)
        for f in self.frames:
            if f.p_file:
                print(f"{f.idx:<6} {f.p_file.file_id:<20} {f.idx:<8} {f.dirty:<6} Occupied")
            else:
                print(f"{f.idx:<6} {'-':<20} {'-':<8} False   Free")

        print("\n2. PAGE DIRECTORY SUMMARY")
        print("-" * 70)
        summary = self.page_directory.get_summary()
        for table_idx, count in summary.items():
            print(f"Page Table {table_idx:<5} → {count} pages mapped")

        print("\n3. STATISTICS")
        print("-" * 70)
        total = self.stats['hits'] + self.stats['faults']
        hit_ratio = (self.stats['hits'] / total * 100) if total > 0 else 0
        print(f"Total Accesses   : {total}")
        print(f"Page Hits        : {self.stats['hits']}")
        print(f"Page Faults      : {self.stats['faults']}")
        print(f"Hit Ratio        : {hit_ratio:.2f}%")
        print(f"TLB Hits         : {self.stats['tlb_hits']}")
        print(f"Writebacks       : {self.stats['writebacks']}")
        print("="*90)