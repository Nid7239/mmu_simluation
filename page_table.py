# page_table.py
from datetime import datetime
from typing import Optional, Dict

class PageTableEntry:
    def __init__(self, frame_idx: int, timestamp: datetime):
        self.frame_idx = frame_idx
        self.timestamp = timestamp
        self.dirty = False

# ==================== Level 3 ====================
class PageTableLevel3:
    def __init__(self):
        self.entries: Dict[int, PageTableEntry] = {}

    def get(self, idx: int) -> Optional[PageTableEntry]:
        return self.entries.get(idx)

    def map(self, idx: int, frame_idx: int, timestamp: datetime):
        self.entries[idx] = PageTableEntry(frame_idx, timestamp)

    def unmap(self, idx: int):
        self.entries.pop(idx, None)

# ==================== Level 2 ====================
class PageTableLevel2:
    def __init__(self):
        self.level3: Dict[int, PageTableLevel3] = {}

    def get_or_create(self, idx: int) -> PageTableLevel3:
        if idx not in self.level3:
            self.level3[idx] = PageTableLevel3()
        return self.level3[idx]

    def get(self, idx: int) -> Optional[PageTableLevel3]:
        return self.level3.get(idx)

# ==================== Level 1 ====================
class PageTableLevel1:
    def __init__(self):
        self.level2: Dict[int, PageTableLevel2] = {}

    def get_or_create(self, idx: int) -> PageTableLevel2:
        if idx not in self.level2:
            self.level2[idx] = PageTableLevel2()
        return self.level2[idx]

    def get(self, idx: int) -> Optional[PageTableLevel2]:
        return self.level2.get(idx)

# ==================== Top Level Directory ====================
class PageDirectory:
    def __init__(self):
        self.files: Dict[str, PageTableLevel1] = {}

    def _split(self, page_idx: int) -> tuple[int, int, int]:
        """Splits a logical page index into 3 distinct hierarchical lookup keys using bitwise shifts."""
        l1 = (page_idx >> 10) & 0x3F
        l2 = (page_idx >> 5) & 0x1F
        l3 = page_idx & 0x1F
        return l1, l2, l3

    def get(self, file_id: str, page_idx: int) -> Optional[PageTableEntry]:
        if file_id not in self.files:
            return None
        l1, l2, l3 = self._split(page_idx)
        level1 = self.files[file_id]
        level2 = level1.get(l1)
        if not level2:
            return None
        level3 = level2.get(l2)
        if not level3:
            return None
        return level3.get(l3)

    def map(self, file_id: str, page_idx: int, frame_idx: int, timestamp: datetime):
        if file_id not in self.files:
            self.files[file_id] = PageTableLevel1()
        l1, l2, l3 = self._split(page_idx)
        level2 = self.files[file_id].get_or_create(l1)
        level3 = level2.get_or_create(l2)
        level3.map(l3, frame_idx, timestamp)

    def unmap(self, file_id: str, page_idx: int):
        if file_id in self.files:
            l1, l2, l3 = self._split(page_idx)
            level2 = self.files[file_id].get(l1)
            if level2:
                level3 = level2.get(l2)
                if level3:
                    level3.unmap(l3)