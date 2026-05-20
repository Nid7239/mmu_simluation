# frame.py
from constants import PAGE_SIZE
from typing import Optional

class Frame:
    """Physical Frame: A container for a 4KB (or specified PAGE_SIZE) memory block."""
    def __init__(self, idx: int):
        self.idx: int = idx
        self.data: bytes = b'\0' * PAGE_SIZE       
        self.file_id: Optional[str] = None
        self.page_idx: Optional[int] = None        
        self.dirty: bool = False
        self.timestamp: str = "-"  # Tracks real-world clock time

    def clear(self):
        """Resets the frame to a free state."""
        self.data = b'\0' * PAGE_SIZE
        self.file_id = None
        self.page_idx = None
        self.dirty = False
        self.timestamp = "-"