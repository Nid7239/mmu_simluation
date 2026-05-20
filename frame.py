from constants import PAGE_SIZE
from typing import Optional

class Frame:
    """Physical Frame"""
    def __init__(self, idx: int):
        self.idx: int = idx
        self.data: bytes = b'\0' * PAGE_SIZE      # ← Now it will work
        self.p_file = None
        self.dirty: bool = False

    def clear(self):
        self.data = b'\0' * PAGE_SIZE
        self.p_file = None
        self.dirty = False