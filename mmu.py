# mmu.py
from datetime import datetime
from frame import Frame
from page_table import PageDirectory 
from constants import NUM_FRAMES

class MMU:
    def __init__(self):
        self.frames = [Frame(i) for i in range(NUM_FRAMES)]
        self.access_counter = 0
        self.page_directory = PageDirectory() 
        self.stats = {'hits': 0, 'faults': 0, 'writebacks': 0}

    def access(self, file_obj, page_idx: int, mode: str = 'READ'):
        self.access_counter += 1
        current_real_time = datetime.now().strftime("%H:%M:%S.%f")
        file_id = str(file_obj.file_id) if hasattr(file_obj, 'file_id') else str(file_obj)
        
        pte = self.page_directory.get(file_id, page_idx)
        
        if pte is not None:
            self.stats['hits'] += 1
            frame = self.frames[pte.frame_idx]
            frame.timestamp = current_real_time
            if mode == 'WRITE':
                frame.dirty = True
                pte.dirty = True
            return

        self.stats['faults'] += 1
        
        # Scenario A: Find free frame
        for frame in self.frames:
            if frame.file_id is None:
                frame.file_id = file_id
                frame.page_idx = page_idx
                frame.timestamp = current_real_time
                frame.dirty = (mode == 'WRITE')
                
                if hasattr(file_obj, 'read_page_data'):
                    frame.data = file_obj.read_page_data(page_idx)
                
                self.page_directory.map(file_id, page_idx, frame.idx, datetime.now())
                return

        # Scenario B: Eviction (LRU)
        victim_frame = min(self.frames, key=lambda f: f.timestamp if f.timestamp != "-" else "99:99:99.999999")
        
        if victim_frame.dirty:
            self.stats['writebacks'] += 1
            if hasattr(file_obj, 'write_page_data'):
                file_obj.write_page_data(victim_frame.page_idx, victim_frame.data)

        self.page_directory.unmap(victim_frame.file_id, victim_frame.page_idx)

        victim_frame.file_id = file_id
        victim_frame.page_idx = page_idx
        victim_frame.timestamp = current_real_time
        victim_frame.dirty = (mode == 'WRITE')
        
        if hasattr(file_obj, 'read_page_data'):
            victim_frame.data = file_obj.read_page_data(page_idx)
        
        self.page_directory.map(file_id, page_idx, victim_frame.idx, datetime.now())

    def dump(self):
        """Prints the comprehensive MMU Simulation state."""
        print("MMU SIMULATION RESULT - MULTI-LEVEL STRUCTURAL ARCHITECTURE VIEW")
        print("==========================================================================================================")
        print(f"{'Frame':<8} {'File ID':<20} {'Page':<8} {'Dirty':<8} {'Status':<12} {'Last System Access Time':<25}")
        print("-" * 115)
        for frame in self.frames:
            status = "Occupied" if frame.file_id else "Free"
            print(f"{frame.idx:<8} {str(frame.file_id):<20} {str(frame.page_idx):<8} {str(frame.dirty):<8} {status:<12} {str(frame.timestamp):<25}")
        print("\n==========================================================================================\n")

    def dump(self):
        """Displays both the Frame Table and the 3-Level Page Table hierarchy."""
        print("\n=== 1. PHYSICAL RAM (FRAME TABLE) ===")
        print(f"{'Frame':<8} {'File ID':<20} {'Page':<8} {'Dirty':<8} {'Status':<12} {'Last Access Time':<25}")
        print("-" * 115)
        for frame in self.frames:
            status = "Occupied" if frame.file_id else "Free"
            print(f"{frame.idx:<8} {str(frame.file_id):<20} {str(frame.page_idx):<8} {str(frame.dirty):<8} {status:<12} {str(frame.timestamp):<25}")

        print("\n=== 2. THREE-LEVEL PAGE TABLE HIERARCHICAL TREE ===")
        # We iterate through the root directory (files)
        for file_id, level1 in self.page_directory.files.items():
            print(f"File: {file_id}")
            for l1_idx, level2 in level1.level2.items():
                print(f"  ├── Level 1 [{l1_idx}]")
                for l2_idx, level3 in level2.level3.items():
                    print(f"  │    └── Level 2 [{l2_idx}]")
                    for l3_idx, pte in level3.entries.items():
                        print(f"  │          └── Level 3 [{l3_idx}] ──► Frame [{pte.frame_idx}]")
        print("==========================================================================================\n")