from datetime import datetime
from frame import Frame
from page_table import PageDirectory 
from constants import NUM_FRAMES
from lru_bst import LRUBST  # Ensure this file is in the same directory

class MMU:
    def __init__(self):
        self.frames = [Frame(i) for i in range(NUM_FRAMES)]
        self.lru_tree = LRUBST() # Tree to track access order
        self.access_counter = 0
        self.page_directory = PageDirectory()
        self.stats = {'hits': 0, 'faults': 0, 'writebacks': 0}

    def access(self, file_obj, page_idx: int, mode: str = 'READ'):
        self.access_counter += 1
        current_real_time = datetime.now() # Use datetime object for accurate sorting
        file_id = str(file_obj.file_id) if hasattr(file_obj, 'file_id') else str(file_obj)
        
        pte = self.page_directory.get(file_id, page_idx)

        # Hit: Update timestamp in frame and the BST
        if pte is not None:
            self.stats['hits'] += 1
            frame = self.frames[pte.frame_idx]
            frame.timestamp = current_real_time.strftime("%H:%M:%S.%f")
            self.lru_tree.insert((file_id, page_idx), current_real_time)
            if mode == 'WRITE':
                frame.dirty = True
                pte.dirty = True
            return

        self.stats['faults'] += 1
        
        # Scenario A: Free Frame
        for frame in self.frames:
            if frame.file_id is None:
                self._map_to_frame(frame, file_obj, file_id, page_idx, mode, current_real_time)
                return

        # Scenario B: Eviction (using BST)
        victim_key = self.lru_tree.remove_oldest()
        victim_frame = next(f for f in self.frames if (f.file_id, f.page_idx) == victim_key)
        
        if victim_frame.dirty:
            self.stats['writebacks'] += 1
            if hasattr(file_obj, 'write_page_data'):
                file_obj.write_page_data(victim_frame.page_idx, victim_frame.data)

        self.page_directory.unmap(victim_frame.file_id, victim_frame.page_idx)
        self._map_to_frame(victim_frame, file_obj, file_id, page_idx, mode, current_real_time)

    def _map_to_frame(self, frame, file_obj, file_id, page_idx, mode, timestamp):
        frame.file_id = file_id
        frame.page_idx = page_idx
        frame.timestamp = timestamp.strftime("%H:%M:%S.%f")
        frame.dirty = (mode == 'WRITE')
        if hasattr(file_obj, 'read_page_data'):
            frame.data = file_obj.read_page_data(page_idx)
        
        self.page_directory.map(file_id, page_idx, frame.idx, timestamp)
        self.lru_tree.insert((file_id, page_idx), timestamp)
    def dump(self):
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