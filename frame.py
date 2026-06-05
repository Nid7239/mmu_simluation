"""
frame.py
========
A physical frame represents one fixed-size slot in simulated RAM.

A frame holds *only* raw bytes and occupancy state.
All higher-level metadata (file identity, virtual page number,
access time, dirty flag) belongs to the PageTableEntry, not here.
"""

from constants import PAGE_SIZE


class Frame:
    """One physical frame in simulated RAM."""

    def __init__(self, idx: int) -> None:
        self.idx:    int   = idx
        self.data:   bytes = b'\x00' * PAGE_SIZE
        self.in_use: bool  = False

    # ------------------------------------------------------------------

    def load(self, data: bytes) -> None:
        """Write page data into this frame and mark it occupied."""
        self.data   = data[:PAGE_SIZE].ljust(PAGE_SIZE, b'\x00')
        self.in_use = True

    def clear(self) -> None:
        """Wipe the frame and mark it free."""
        self.data   = b'\x00' * PAGE_SIZE
        self.in_use = False

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "occupied" if self.in_use else "free"
        return f"Frame(idx={self.idx}, {status})"
