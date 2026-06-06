"""
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
    # ------------------------------------------------------------------

    @staticmethod
    def _split_vpn(vpn: int) -> tuple[int, int]:
        """
        Split vpn into (l1_idx, l2_idx).

        Example: vpn=70 → binary=01000110
          bit 7     = 0  → L1_Table_0
          bits 6-5  = 10 → L2_T2
          bits 4-0  = 00110 → slot (routing only)
        """
        l1_idx = (vpn >> (L2_BITS + SLOT_BITS)) & ((1 << L1_BITS) - 1)
        l2_idx = (vpn >> SLOT_BITS)             & ((1 << L2_BITS) - 1)
        return l1_idx % PAGE_TABLES_L1, l2_idx % PAGE_TABLES_L2

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

        Traversal (strict — no level skipping):
          PageDirectory → L1_Table[l1_idx] → L2_T[l2_idx] → entry
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        # Step 1: Directory → L1 only
        l1 = self._get_l1(l1_idx)
        if l1 is None:
            return None

        # Step 2: L1 → L2 only (directory never does this step)
        l2 = l1.get_l2(l2_idx)
        if l2 is None:
            return None

        # Step 3: L2 → entry
        return l2.get(file_id, vpn)

    def map(
        self,
        file_id:   str,
        vpn:       int,
        frame_idx: int,
        timestamp: datetime,
    ) -> PageTableEntry:
        """
        Insert mapping (file_id, vpn) → frame_idx.
        Allocates L1 and L2 on demand.

        Traversal:
          PageDirectory → L1_Table[l1_idx] → L2_T[l2_idx] → map
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        # Step 1: Directory → L1
        l1 = self._get_or_create_l1(l1_idx)

        # Step 2: L1 → L2
        l2 = l1.get_or_create_l2(l2_idx)

        # Step 3: L2 → create entry
        return l2.map(file_id, vpn, frame_idx, timestamp)

    def unmap(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """
        Remove mapping for (file_id, vpn).
        Prunes empty tables bottom-up.
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        l1 = self._get_l1(l1_idx)
        if l1 is None:
            return None

        l2 = l1.get_l2(l2_idx)
        if l2 is None:
            return None

        entry = l2.unmap(file_id, vpn)

        # Prune bottom-up: L2 first, then L1
        l1.prune_l2_if_empty(l2_idx)
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