from datetime import datetime
from typing import Optional, Dict

class PageTableEntry:
    def __init__(self, frame_idx: int, timestamp: datetime):
        self.frame_idx = frame_idx
        self.timestamp = timestamp
        self.dirty = False

class PageTable:
    def __init__(self):
        self.entries: Dict[int, PageTableEntry] = {}

    def get(self, page_idx: int) -> Optional[PageTableEntry]:
        return self.entries.get(page_idx)

    def map(self, page_idx: int, frame_idx: int, timestamp: datetime):
        self.entries[page_idx] = PageTableEntry(frame_idx, timestamp)

    def unmap(self, page_idx: int):
        self.entries.pop(page_idx, None)