"""
page_table.py
=============
Level-2 page table (L2_T0 to L2_T7 in the diagram).

          [PageDirectory]
           /            \
    [L1_Table_0]    [L1_Table_1]
    /   |   |   \    /   |   |   \
  L2   L2  L2  L2  L2  L2  L2  L2
  T0   T1  T2  T3  T4  T5  T6  T7

Each L2 table maps (file_id, vpn) → PageTableEntry → frame.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Iterator

from page_table_entry import PageTableEntry

_Key = tuple[str, int]   # (file_id, vpn)


class L2PageTable:
    """One L2 page table — bottom level of the hierarchy."""

    def __init__(self, table_id: str) -> None:
        self.table_id = table_id
        self._entries: dict[_Key, PageTableEntry] = {}

    def get(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        return self._entries.get((file_id, vpn))

    def map(self, file_id: str, vpn: int, frame_idx: int, timestamp: datetime) -> PageTableEntry:
        entry = PageTableEntry(frame_idx, file_id, vpn, timestamp)
        self._entries[(file_id, vpn)] = entry
        return entry

    def unmap(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        return self._entries.pop((file_id, vpn), None)

    @property
    def is_empty(self) -> bool:
        return len(self._entries) == 0

    def count(self) -> int:
        return len(self._entries)

    def entries(self) -> Iterator[tuple[_Key, PageTableEntry]]:
        yield from self._entries.items()

    def __repr__(self) -> str:
        return f"L2PageTable({self.table_id!r}, entries={len(self._entries)})"