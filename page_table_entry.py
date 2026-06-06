from __future__ import annotations
from datetime import datetime


class PageTableEntry:
    """
    Metadata record for one mapped virtual page.

    Attributes
    ----------
    frame_idx   : Index of the physical frame that holds this page's data.
    file_id     : Identifier of the PhysicalFile that owns this page.
    vpn         : Virtual page number (needed for writeback).
    dirty       : True when the page has been written since it was loaded.
    last_access : Timestamp of the most recent read or write (used by LRU).
    """

    def __init__(
        self,
        frame_idx:   int,
        file_id:     str,
        vpn:         int,
        last_access: datetime,
    ) -> None:
        self.frame_idx:   int      = frame_idx
        self.file_id:     str      = file_id
        self.vpn:         int      = vpn
        self.dirty:       bool     = False
        self.last_access: datetime = last_access

    def touch(self, ts: datetime) -> None:
        """Update the last-access timestamp on a cache hit."""
        self.last_access = ts

    def __repr__(self) -> str:
        return (
            f"PTE(frame={self.frame_idx}, file={self.file_id!r}, "
            f"vpn={self.vpn}, dirty={self.dirty})"
        )