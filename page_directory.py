"""
page_directory.py
=================
Three-level page table hierarchy.

Structure
---------
Level 0 : PageDirectory   — 1 instance, the single root
Level 1 : L1PageTable     — PAGE_TABLES_L1 (2) slots inside the directory
Level 2 : PageTable       — PAGE_TABLES_L2 (4) slots inside each L1 table

Strict traversal rule (matches the mentor's diagram)
-----------------------------------------------------
  PageDirectory  →  L1PageTable[l1_idx]  →  PageTable[l2_idx]  →  entry

  • PageDirectory  only holds references to L1 tables.
  • L1PageTable    only holds references to L2 (PageTable) instances.
  • PageDirectory  never skips a level and touches L2 or entries directly.

VPN bit-splitting  (routes to the correct L2 table)
----------------------------------------------------
  Bit  7      → l1_idx   (1 bit  → 2 L1 tables)
  Bits 6–5    → l2_idx   (2 bits → 4 L2 tables)
  Bits 4–0    → slot     (used only for routing; not the intra-table key)

Within each L2 PageTable, entries are keyed by the full (file_id, vpn)
pair, so different files whose VPNs produce the same slot never collide.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from page_table import PageTable
from page_table_entry import PageTableEntry
from constants import PAGE_TABLES_L1, PAGE_TABLES_L2, L1_BITS, L2_BITS, SLOT_BITS


# ---------------------------------------------------------------------------
#  Level-1 page table
# ---------------------------------------------------------------------------

class L1PageTable:
    """
    Level-1 page table.

    Owns a fixed-size array of PAGE_TABLES_L2 Level-2 PageTable slots.
    Only L1PageTable creates and exposes L2 tables — the PageDirectory
    never accesses L2 directly.
    """

    def __init__(self, l1_idx: int) -> None:
        self.l1_idx: int = l1_idx
        self._l2_tables: list[Optional[PageTable]] = [None] * PAGE_TABLES_L2

    # ------------------------------------------------------------------
    #  L2 access — the only methods PageDirectory calls on L1
    # ------------------------------------------------------------------

    def get_l2(self, l2_idx: int) -> Optional[PageTable]:
        """Return the L2 table at *l2_idx*, or None if not yet allocated."""
        return self._l2_tables[l2_idx]

    def get_or_create_l2(self, l2_idx: int) -> PageTable:
        """Return the L2 table at *l2_idx*, allocating it on first use."""
        if self._l2_tables[l2_idx] is None:
            self._l2_tables[l2_idx] = PageTable(f"L2[{self.l1_idx}][{l2_idx}]")
        return self._l2_tables[l2_idx]

    def prune_l2_if_empty(self, l2_idx: int) -> None:
        """Free the L2 table at *l2_idx* if it has no remaining entries."""
        tbl = self._l2_tables[l2_idx]
        if tbl is not None and tbl.is_empty:
            self._l2_tables[l2_idx] = None

    # ------------------------------------------------------------------
    #  Introspection
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return all(t is None or t.is_empty for t in self._l2_tables)

    def summary(self) -> dict[int, int]:
        """Return {l2_idx: entry_count} for non-empty L2 tables."""
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
    Level-0 page directory — the single root of the page table hierarchy.

    Owns a fixed-size array of PAGE_TABLES_L1 L1PageTable slots and
    exposes the three public operations the MMU needs: get, map, unmap.

    The directory only ever references Level-1 tables.  All deeper
    traversal is delegated through L1PageTable.
    """

    def __init__(self) -> None:
        self._l1_tables: list[Optional[L1PageTable]] = [None] * PAGE_TABLES_L1

    # ------------------------------------------------------------------
    #  VPN bit-splitting  (determines which L1/L2 table to walk)
    # ------------------------------------------------------------------

    @staticmethod
    def _split_vpn(vpn: int) -> tuple[int, int]:
        """
        Decompose *vpn* into (l1_idx, l2_idx) for table routing.

        Bit layout:
          Bit  7      → l1_idx  (selects the L1 table)
          Bits 6–5    → l2_idx  (selects the L2 table within L1)
          Bits 4–0    → not used for routing; entries are keyed by
                        (file_id, vpn) inside L2 to prevent collisions.
        """
        l1_idx = (vpn >> (L2_BITS + SLOT_BITS)) & ((1 << L1_BITS) - 1)
        l2_idx = (vpn >> SLOT_BITS)             & ((1 << L2_BITS) - 1)
        return l1_idx % PAGE_TABLES_L1, l2_idx % PAGE_TABLES_L2

    # ------------------------------------------------------------------
    #  Internal — only PageDirectory touches the L1 array
    # ------------------------------------------------------------------

    def _get_l1(self, l1_idx: int) -> Optional[L1PageTable]:
        return self._l1_tables[l1_idx]

    def _get_or_create_l1(self, l1_idx: int) -> L1PageTable:
        if self._l1_tables[l1_idx] is None:
            self._l1_tables[l1_idx] = L1PageTable(l1_idx)
        return self._l1_tables[l1_idx]

    # ------------------------------------------------------------------
    #  Public interface used by the MMU
    # ------------------------------------------------------------------

    def get(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """
        Look up the entry for (file_id, vpn).

        Traversal: Directory → L1[l1_idx] → L2[l2_idx] → entry(file_id, vpn)
        Returns None at the first missing level or if the entry is absent.
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        l1 = self._get_l1(l1_idx)           # Directory → L1
        if l1 is None:
            return None

        l2 = l1.get_l2(l2_idx)              # L1 → L2  (directory never skips to L2)
        if l2 is None:
            return None

        return l2.get(file_id, vpn)          # L2 → entry

    def map(
        self,
        file_id:   str,
        vpn:       int,
        frame_idx: int,
        timestamp: datetime,
    ) -> PageTableEntry:
        """
        Insert a mapping for (file_id, vpn) → frame_idx.

        Allocates L1 and L2 tables on demand.
        Traversal: Directory → L1[l1_idx] → L2[l2_idx] → map(file_id, vpn)
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        l1 = self._get_or_create_l1(l1_idx)      # Directory → L1
        l2 = l1.get_or_create_l2(l2_idx)          # L1 → L2
        return l2.map(file_id, vpn, frame_idx, timestamp)

    def unmap(self, file_id: str, vpn: int) -> Optional[PageTableEntry]:
        """
        Remove the mapping for (file_id, vpn) and return the old entry.

        Prunes empty L2 and L1 tables upward to reclaim memory.
        """
        l1_idx, l2_idx = self._split_vpn(vpn)

        l1 = self._get_l1(l1_idx)
        if l1 is None:
            return None

        l2 = l1.get_l2(l2_idx)
        if l2 is None:
            return None

        entry = l2.unmap(file_id, vpn)

        # Prune empty tables bottom-up
        l1.prune_l2_if_empty(l2_idx)
        if l1.is_empty:
            self._l1_tables[l1_idx] = None

        return entry

    # ------------------------------------------------------------------
    #  Reporting helpers
    # ------------------------------------------------------------------

    def get_summary(self) -> dict[int, dict[int, int]]:
        """Return {l1_idx: {l2_idx: entry_count}} for non-empty tables."""
        return {
            i: l1.summary()
            for i, l1 in enumerate(self._l1_tables)
            if l1 is not None and not l1.is_empty
        }

    def total_mapped(self) -> int:
        """Total number of currently mapped pages across the whole hierarchy."""
        return sum(
            count
            for l2_summary in self.get_summary().values()
            for count in l2_summary.values()
        )

    def __repr__(self) -> str:
        active = sum(1 for l1 in self._l1_tables if l1 and not l1.is_empty)
        return f"PageDirectory(active_l1={active}/{PAGE_TABLES_L1})"
