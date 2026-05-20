# mmu.py
from datetime import datetime
from frame import Frame
from page_table import PageDirectory 
from constants import NUM_FRAMES

class MMU:
    def __init__(self):
        # Initialize frames using the separate Frame class
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
            # --- PAGE HIT ---
            self.stats['hits'] += 1
            frame = self.frames[pte.frame_idx]
            frame.timestamp = current_real_time
            if mode == 'WRITE':
                frame.dirty = True
                pte.dirty = True
            return

        # --- PAGE FAULT ---
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
                # Note: In a real multi-file system, keep a mapping of frame to file_obj
                file_obj.write_page_data(victim_frame.page_idx, victim_frame.data)

        self.page_directory.unmap(victim_frame.file_id, victim_frame.page_idx)

        # Recycling the frame container
        victim_frame.file_id = file_id
        victim_frame.page_idx = page_idx
        victim_frame.timestamp = current_real_time
        victim_frame.dirty = (mode == 'WRITE')
        
        if hasattr(file_obj, 'read_page_data'):
            victim_frame.data = file_obj.read_page_data(page_idx)
        
        self.page_directory.map(file_id, page_idx, victim_frame.idx, datetime.now())