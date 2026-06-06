
from __future__ import annotations
import sys
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from frame import Frame

_SEP_WIDE   = "=" * 80
_SEP_NARROW = "─" * 80
_SEP_MID    = "·" * 80


class TraceLogger:
    
    def __init__(self, path: str = "trace.log") -> None:
        self._fh   = open(path, "w", encoding="utf-8")
        self._seq  = 0          # monotonic access counter
        self._real = sys.stdout # keep a reference to real stdout

        self._write(_SEP_WIDE)
        self._write("MMU INTERNAL TRACE LOG")
        self._write(f"Started : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
        self._write(_SEP_WIDE)
        self._write("")

    # ------------------------------------------------------------------
    #  Main trace entry — called once per access()
    # ------------------------------------------------------------------

    def log_access(
        self,
        *,
        file_id:    str,
        vpn:        int,
        op:         str,           # "READ" or "WRITE"
        l1_idx:     int,
        l2_idx:     int,
        resolution: str,           # "TLB_HIT" | "PT_HIT" | "PAGE_FAULT"
        frame_idx:  int,
        dirty_after: bool,
    ) -> None:
        self._seq += 1
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        self._write(f"[{self._seq:>4}]  {ts}  {op:<5}  {file_id}  vpn={vpn}")
        self._write(
            f"        VPN split  →  L1[{l1_idx}]  →  L2[{l2_idx}]"
        )

        if resolution == "TLB_HIT":
            self._write(f"        TLB HIT    →  frame {frame_idx}  (no page-table walk needed)")
        elif resolution == "PT_HIT":
            self._write(
                f"        TLB MISS   →  page-table walk  →  HIT in L2  →  frame {frame_idx}"
            )
            self._write(f"        TLB updated with new entry")
        else:  # PAGE_FAULT
            self._write(
                f"        TLB MISS   →  page-table walk  →  MISS  →  PAGE FAULT"
            )
            self._write(
                f"        Page loaded from disk  →  frame {frame_idx} allocated"
            )
            self._write(
                f"        Page table updated: L1[{l1_idx}] → L2[{l2_idx}] → frame {frame_idx}"
            )
            self._write(f"        TLB updated with new entry")

        if op == "WRITE":
            self._write(f"        Write applied  →  dirty bit SET on PTE")

        self._write(f"        Resolved to frame {frame_idx}  (dirty={dirty_after})")
        self._write(_SEP_MID)

    # ------------------------------------------------------------------
    #  Eviction notice — called before a victim is displaced
    # ------------------------------------------------------------------

    def log_eviction(
        self,
        *,
        victim_file: str,
        victim_vpn:  int,
        victim_frame: int,
        was_dirty:   bool,
        incoming_file: str,
        incoming_vpn:  int,
    ) -> None:
        dirty_note = "  ← DIRTY — writeback required" if was_dirty else "  (clean)"
        self._write(
            f"        EVICT  frame {victim_frame}  "
            f"({victim_file}  vpn={victim_vpn}){dirty_note}"
        )
        self._write(
            f"               to make room for  ({incoming_file}  vpn={incoming_vpn})"
        )

    # ------------------------------------------------------------------
    #  Writeback notice
    # ------------------------------------------------------------------

    def log_writeback(self, *, file_id: str, vpn: int, frame_idx: int) -> None:
        self._write(
            f"        WRITEBACK  frame {frame_idx}  →  disk  "
            f"({file_id}  vpn={vpn})"
        )

    # ------------------------------------------------------------------
    #  Frame snapshot — printed after every access
    # ------------------------------------------------------------------

    def log_frame_snapshot(self, frames: "list[Frame]") -> None:
        """Print the full physical frame table as it stands right now."""
        self._write("")
        self._write("  Physical Frame Table (RAM snapshot)")
        self._write(f"  {'Frame':<7} {'Status':<10} {'File':<22} {'VPN':<6} {'Dirty'}")
        self._write("  " + "─" * 56)

        # We only know occupancy and basic state here — the MMU passes
        # the entry info via log_access; for the snapshot we use what
        # frames carry directly (in_use flag).  The MMU monkey-patches
        # _snapshot_entries before calling this so we can show PTE data.
        for f in frames:
            if f.in_use and hasattr(f, "_snap_file"):
                dirty_str = str(f._snap_dirty)
                self._write(
                    f"  {f.idx:<7} {'occupied':<10} {f._snap_file:<22} "
                    f"{f._snap_vpn:<6} {dirty_str}"
                )
            elif f.in_use:
                self._write(
                    f"  {f.idx:<7} {'occupied':<10} {'(unknown)':<22} {'?':<6} ?"
                )
            else:
                self._write(f"  {f.idx:<7} {'free':<10} {'-':<22} {'-':<6} -")
        self._write("")

    # ------------------------------------------------------------------
    #  Final summary banner
    # ------------------------------------------------------------------

    def log_final(self, stats: dict[str, int]) -> None:
        self._write(_SEP_WIDE)
        self._write("TRACE COMPLETE — FINAL STATISTICS")
        self._write(_SEP_WIDE)
        total   = stats["hits"] + stats["faults"]
        hit_pct = (stats["hits"] / total * 100) if total else 0.0
        tlb_tot = stats["tlb_hits"] + stats["tlb_misses"]
        tlb_pct = (stats["tlb_hits"] / tlb_tot * 100) if tlb_tot else 0.0

        self._write(f"  Total accesses : {total}")
        self._write(f"  Page hits      : {stats['hits']}  ({hit_pct:.1f}%)")
        self._write(f"  Page faults    : {stats['faults']}")
        self._write(f"  TLB hits       : {stats['tlb_hits']}  ({tlb_pct:.1f}%)")
        self._write(f"  TLB misses     : {stats['tlb_misses']}")
        self._write(f"  Writebacks     : {stats['writebacks']}")
        self._write(_SEP_WIDE)

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _write(self, line: str) -> None:
        print(line, file=self._fh)

    def close(self) -> None:
        self._fh.flush()
        self._fh.close()