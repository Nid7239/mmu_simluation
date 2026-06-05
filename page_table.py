"""
page_table.py
=============
A Level-2 page table.

Each instance maps (file_id, vpn) pairs to PageTableEntry objects.
The slot derived from VPN bit-splitting routes the MMU to the *correct*
L2 table; within that table entries are keyed by the full (file_id, vpn)
pair so that different files whose VPNs hash to the same slot never
overwrite each other.

Multiple PageTable instances exist per L1PageTable (PAGE_TABLES_L2 of
them), and multiple L1PageTables exist inside the PageDirectory
(PAGE_TABLES_L1 of them).
"""

from __future__ import annotations
from datetime import datetime
from typing import Iterator, Optional

from page_table_entry import PageTableEntry

# Key type used inside each L2 table
_Key = tuple[str, int]   # (file_id, vpn)


class PageTable:
    """
    Level-2 page table.

    Maps (file_id, vpn) pairs to PageTableEntry objects.  The VPN bit-
    split routes traffic to the right instance; collision avoidance within
    the table is achieved by keying on the full (file_id, vpn) pair.
    """

    def __init__(self, table_id: str) -> None:
        self.table_id: str                    = table_id
        self._entries: dict[_Key, PageTableEntry] = {}

    # ------------------------------------------------------------------
    #  Core operations
    # ------------------------------------------------------------------

    def get(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """Return the entry for *(file_id, vpn)*, or None if unmapped."""
        return self._entries.get((file_id, vpn))

    def map(
        self,
        file_id:   str,
        vpn:       int,
        frame_idx: int,
        timestamp: datetime,
    ) -> PageTableEntry:
        """
        Create a PageTableEntry for *(file_id, vpn)* and return it.

        Overwrites any pre-existing entry (the caller is responsible for
        unmapping before re-mapping when evicting).
        """
        entry = PageTableEntry(frame_idx, file_id, vpn, timestamp)
        self._entries[(file_id, vpn)] = entry
        return entry

    def unmap(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """Remove and return the entry for *(file_id, vpn)*, or None if absent."""
        return self._entries.pop((file_id, vpn), None)

    # ------------------------------------------------------------------
    #  Introspection helpers
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return len(self._entries) == 0

    def count(self) -> int:
        return len(self._entries)

    def entries(self) -> Iterator[tuple[_Key, PageTableEntry]]:
        """Yield ((file_id, vpn), entry) pairs."""
        yield from self._entries.items()

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PageTable({self.table_id!r}, entries={len(self._entries)})"
