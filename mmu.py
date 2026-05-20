from datetime import datetime
import sys
from typing import Tuple
from frame import Frame
from page_table import PageDirectory
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

        self.log_file = open("output.log", "w", encoding="utf-8")
        sys.stdout = self.log_file

    def access(self, p_file: PhysicalFile, page_idx: int, write_data: bytes = None):
        key: Tuple[str, int] = (p_file.file_id, page_idx)
        now = datetime.now()

        # TLB + Page Table Logic
        if key in self.tlb:
            self.stats["tlb_hits"] += 1
            self.stats["hits"] += 1
            frame_idx = self.tlb[key]
        else:
            self.stats["tlb_misses"] += 1
            entry = self.page_directory.get(p_file.file_id, page_idx)
            if entry:
                self.stats["hits"] += 1
                frame_idx = entry.frame_idx
                self.tlb[key] = frame_idx
            else:
                self.stats["faults"] += 1
                frame = self._evict_or_get_free(p_file.file_id, page_idx)
                frame_idx = frame.idx

                frame.data = p_file.read_page(page_idx)
                frame.p_file = p_file
                frame.dirty = False

                self.page_directory.map(p_file.file_id, page_idx, frame_idx, now)
                self.tlb[key] = frame_idx

        self.lru.insert(key, now)

        frame = self.frames[frame_idx]
        if write_data:
            frame.data = write_data
            frame.dirty = True

        return frame.data

    def _evict_or_get_free(self, file_id: str, page_idx: int) -> Frame:
        for frame in self.frames:
            if frame.p_file is None:
                return frame

        # LRU Eviction
        victim_key = self.lru.remove_oldest()
        v_file, v_page = victim_key
        entry = self.page_directory.get(v_file, v_page)
        frame_idx = entry.frame_idx if entry else 0
        frame = self.frames[frame_idx]

        if frame.dirty and frame.p_file:
            self.stats["writebacks"] += 1
            frame.p_file.write_page(v_page, frame.data)

        self.tlb.pop(victim_key, None)
        self.page_directory.unmap(v_file, v_page)
        frame.clear()

        return frame

    def dump(self):
        """Clean Table Format Output"""
        print("\n" + "="*90)
        print("MMU SIMULATION RESULT - TABLE FORMAT")
        print("="*90)

        # Frame Table
        print("\n1. FRAME TABLE")
        print("-" * 80)
        print(f"{'Frame':<6} {'File ID':<20} {'Page':<10} {'Dirty':<8} Status")
        print("-" * 80)
        for f in self.frames:
            if f.p_file:
                print(f"{f.idx:<6} {f.p_file.file_id:<20} {f.idx:<10} {str(f.dirty):<8} Occupied")
            else:
                print(f"{f.idx:<6} {'-':<20} {'-':<10} False     Free")

        # Page Table Summary
        print("\n2. PAGE TABLE SUMMARY")
        print("-" * 80)
        print(f"{'File ID':<25} {'Pages Mapped':<15}")
        print("-" * 80)
        for file_id, level1 in self.page_directory.files.items():
            total_pages = 0
            for l2 in level1.level2.values():
                for l3 in l2.level3.values():
                    total_pages += len(l3.entries)
            print(f"{file_id:<25} {total_pages:<15}")

        # LRU Table
        print("\n3. LRU TABLE (Oldest → Newest)")
        print("-" * 80)
        print(f"{'Rank':<5} {'Key':<30} {'Time'}")
        print("-" * 80)
        try:
            order = []
            def inorder(node, rank):
                if node:
                    inorder(node.left, rank)
                    order.append((rank[0], node))
                    rank[0] += 1
                    inorder(node.right, rank)
            rank = [1]
            inorder(self.lru.root, rank)

            for r, node in order[:20]:
                ts = node.timestamp.strftime("%H:%M:%S")
                print(f"{r:<5} {node.key[0]}_p{node.key[1]:<30} {ts}")
        except:
            print("LRU Empty")

        # Statistics
        print("\n4. STATISTICS")
        print("-" * 80)
        total = self.stats['hits'] + self.stats['faults']
        hit_ratio = (self.stats['hits'] / total * 100) if total > 0 else 0
        print(f"Total Accesses   : {total}")
        print(f"Page Hits        : {self.stats['hits']}")
        print(f"Page Faults      : {self.stats['faults']}")
        print(f"Hit Ratio        : {hit_ratio:.2f}%")
        print(f"TLB Hits         : {self.stats['tlb_hits']}")
        print(f"Writebacks       : {self.stats['writebacks']}")
        print("="*90)