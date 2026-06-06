r"""
page_directory.py
=================
Multi-level page table hierarchy matching this diagram:

          [PageDirectory]
           /            \
    [L1_Table_0]    [L1_Table_1]
    /   |   |   \    /   |   |   \
  L2   L2  L2  L2  L2  L2  L2  L2
  T0   T1  T2  T3  T4  T5  T6  T7

Levels:
  Level 0 : PageDirectory     — 1 instance, root
  Level 1 : L1PageTable       — array of 2  (L1_Table_0, L1_Table_1)
  Level 2 : L2PageTable       — array of 4 per L1 = 8 total (T0 to T7)

Strict rule — each level talks ONLY to the next level:
  PageDirectory → L1PageTable only
  L1PageTable   → L2PageTable only
  L2PageTable   → PageTableEntry → frame

VPN bit-splitting:
  bit  7      → l1_idx  (0 or 1  → L1_Table_0 or L1_Table_1)
  bits 6-5    → l2_idx  (0 to 3  → which L2 table inside that L1)
  bits 4-0    → slot    (routing only)
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from page_table import L2PageTable
from page_table_entry import PageTableEntry
from constants import PAGE_TABLES_L1, PAGE_TABLES_L2, L1_BITS, L2_BITS, SLOT_BITS


# ---------------------------------------------------------------------------
#  Level-1 page table
# ---------------------------------------------------------------------------

class L1PageTable:
    """
    Level-1 page table (L1_Table_0 or L1_Table_1 in diagram).

    Owns an array of 4 L2PageTable instances.
    Only L1 creates and exposes L2 tables.
    PageDirectory never touches L2 directly.
    """

    def __init__(self, l1_idx: int) -> None:
        self.l1_idx = l1_idx
        # Array of 4 L2 tables per L1
        # L1_Table_0 owns: L2_T0, L2_T1, L2_T2, L2_T3
        # L1_Table_1 owns: L2_T4, L2_T5, L2_T6, L2_T7
        self._l2_tables: list[Optional[L2PageTable]] = [None] * PAGE_TABLES_L2

    def get_l2(self, l2_idx: int) -> Optional[L2PageTable]:
        """Return L2 table at index — None if not yet allocated."""
        return self._l2_tables[l2_idx]

    def get_or_create_l2(self, l2_idx: int) -> L2PageTable:
        """Return L2 table at index — allocate on first use."""
        if self._l2_tables[l2_idx] is None:
            # Name it so it's clear in output: L2_T0, L2_T1 etc.
            global_l2_idx = self.l1_idx * PAGE_TABLES_L2 + l2_idx
            self._l2_tables[l2_idx] = L2PageTable(f"L2_T{global_l2_idx}")
        return self._l2_tables[l2_idx]

    def prune_l2_if_empty(self, l2_idx: int) -> None:
        """Free the L2 table if it has no remaining entries."""
        tbl = self._l2_tables[l2_idx]
        if tbl is not None and tbl.is_empty:
            self._l2_tables[l2_idx] = None

    # ------------------------------------------------------------------
    #  L2 routing — ONLY L1 knows how to pick its own L2 table.
    #  The PageDirectory never computes this and never calls L2.
    # ------------------------------------------------------------------

    @staticmethod
    def _split_l2(vpn: int) -> int:
        """Extract the L2 index (bits 6-5) from the VPN."""
        return ((vpn >> SLOT_BITS) & ((1 << L2_BITS) - 1)) % PAGE_TABLES_L2

    # ------------------------------------------------------------------
    #  Delegated operations — the directory calls these on L1 only.
    #  L1 owns the L2 lookup/creation and the call into L2.
    # ------------------------------------------------------------------

    def lookup(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """Directory → L1.lookup → L2.get → entry."""
        l2 = self.get_l2(self._split_l2(vpn))
        return l2.get(file_id, vpn) if l2 is not None else None

    def insert(
        self,
        file_id:   str,
        vpn:       int,
        frame_idx: int,
        timestamp: datetime,
    ) -> PageTableEntry:
        """Directory → L1.insert → L2.map (allocates the L2 on first use)."""
        l2 = self.get_or_create_l2(self._split_l2(vpn))
        return l2.map(file_id, vpn, frame_idx, timestamp)

    def remove(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """Directory → L1.remove → L2.unmap, then prune the L2 if empty."""
        l2_idx = self._split_l2(vpn)
        l2 = self.get_l2(l2_idx)
        if l2 is None:
            return None
        entry = l2.unmap(file_id, vpn)
        self.prune_l2_if_empty(l2_idx)
        return entry

    @property
    def is_empty(self) -> bool:
        return all(t is None or t.is_empty for t in self._l2_tables)

    def summary(self) -> dict[int, int]:
        return {
            i: tbl.count()
            for i, tbl in enumerate(self._l2_tables)
            if tbl is not None and not tbl.is_empty
        }

    def __repr__(self) -> str:
        active = sum(1 for t in self._l2_tables if t and not t.is_empty)
        return f"L1PageTable(idx={self.l1_idx}, active_l2={active}/{PAGE_TABLES_L2})"


# ---------------------------------------------------------------------------
#  Level-0 page directory (root)
# ---------------------------------------------------------------------------

class PageDirectory:
    """
    Level-0 page directory — single root of the hierarchy.

    Owns an array of 2 L1PageTable instances:
      _l1_tables[0] = L1_Table_0
      _l1_tables[1] = L1_Table_1

    PageDirectory ONLY ever talks to L1 tables.
    It never accesses L2 tables or entries directly.
    """

    def __init__(self) -> None:
        # Array of 2 L1 tables — L1_Table_0 and L1_Table_1
        self._l1_tables: list[Optional[L1PageTable]] = [None] * PAGE_TABLES_L1

    # ------------------------------------------------------------------
    #  VPN bit-splitting
    #
    #  The directory ONLY knows how to extract its own level's index
    #  (l1_idx, bit 7).  It does NOT compute l2_idx — that is L1's job.
    # ------------------------------------------------------------------

    @staticmethod
    def _split_l1(vpn: int) -> int:
        """Extract the L1 index (bit 7) from the VPN — the only bit the directory reads."""
        return ((vpn >> (L2_BITS + SLOT_BITS)) & ((1 << L1_BITS) - 1)) % PAGE_TABLES_L1

    @staticmethod
    def decode_route(vpn: int) -> tuple[int, int]:
        """
        Decode (l1_idx, l2_idx) for TRACING / REPORTING only.

        This is a read-only display helper for the trace log — it is NOT
        used during traversal. Real traversal asks each level for its own
        index: the directory uses _split_l1, L1 uses _split_l2.

        Example: vpn=70 → binary=01000110
          bit 7     = 0  → L1_Table_0
          bits 6-5  = 10 → L2_T2
          bits 4-0  = 00110 → slot (not used for table routing)
        """
        return PageDirectory._split_l1(vpn), L1PageTable._split_l2(vpn)

    # ------------------------------------------------------------------
    #  Internal — PageDirectory only touches _l1_tables array
    # ------------------------------------------------------------------

    def _get_l1(self, l1_idx: int) -> Optional[L1PageTable]:
        return self._l1_tables[l1_idx]

    def _get_or_create_l1(self, l1_idx: int) -> L1PageTable:
        if self._l1_tables[l1_idx] is None:
            self._l1_tables[l1_idx] = L1PageTable(l1_idx)
        return self._l1_tables[l1_idx]

    # ------------------------------------------------------------------
    #  Public interface — called by MMU only
    # ------------------------------------------------------------------

    def get(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """
        Look up entry for (file_id, vpn).

        Strict hierarchy — the directory only ever calls an L1 method:
          PageDirectory → L1.lookup → (L1 internally) L2.get → entry
        """
        l1 = self._get_l1(self._split_l1(vpn))
        if l1 is None:
            return None
        return l1.lookup(file_id, vpn)

    def map(
        self,
        file_id:   str,
        vpn:       int,
        frame_idx: int,
        timestamp: datetime,
    ) -> PageTableEntry:
        """
        Insert mapping (file_id, vpn) → frame_idx.

        Strict hierarchy:
          PageDirectory → L1.insert → (L1 internally) L2.map
        The directory allocates the L1 on demand; L1 allocates its own L2.
        """
        l1 = self._get_or_create_l1(self._split_l1(vpn))
        return l1.insert(file_id, vpn, frame_idx, timestamp)

    def unmap(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """
        Remove mapping for (file_id, vpn).

        Strict hierarchy:
          PageDirectory → L1.remove → (L1 internally) L2.unmap + prune L2
        The directory then prunes the L1 itself if it has gone empty.
        """
        l1_idx = self._split_l1(vpn)
        l1 = self._get_l1(l1_idx)
        if l1 is None:
            return None

        entry = l1.remove(file_id, vpn)

        # Directory only prunes its OWN level (L1); L1 already pruned its L2.
        if l1.is_empty:
            self._l1_tables[l1_idx] = None

        return entry

    # ------------------------------------------------------------------
    #  Reporting
    # ------------------------------------------------------------------

    def get_summary(self) -> dict[int, dict[int, int]]:
        return {
            i: l1.summary()
            for i, l1 in enumerate(self._l1_tables)
            if l1 is not None and not l1.is_empty
        }

    def total_mapped(self) -> int:
        return sum(
            count
            for l2_summary in self.get_summary().values()
            for count in l2_summary.values()
        )

    def __repr__(self) -> str:
        active = sum(1 for l1 in self._l1_tables if l1 and not l1.is_empty)
        return f"PageDirectory(active_l1={active}/{PAGE_TABLES_L1})"