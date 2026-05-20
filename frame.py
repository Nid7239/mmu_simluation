
from constants import PAGE_SIZE
from typing import Optional

class Frame:
    def __init__(self, idx: int):
        self.idx: int = idx
        self.data: bytes = b'\0' * PAGE_SIZE       
        self.file_id: Optional[str] = None
        self.page_idx: Optional[int] = None        
        self.dirty: bool = False
        self.timestamp: str = "-"  # Tracks real-world clock time

    def clear(self):
        self.data = b'\0' * PAGE_SIZE
        self.file_id = None
        self.page_idx = None
        self.dirty = False
        self.timestamp = "-"