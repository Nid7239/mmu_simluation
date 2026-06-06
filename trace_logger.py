"""
trace_logger.py
===============
Step-by-step trace of every MMU access, written to trace.log.

This is the detailed "what happened internally" companion to output.log
(which only holds the high-level final state). For each access it records:

  - the VPN routing through the multi-level page table   (which L1 / L2 table)
  - how the translation resolved   (TLB_HIT / PT_HIT / PAGE_FAULT)
  - any eviction + writeback triggered to make room for the new page
  - a snapshot of all physical frames immediately after the access

One "block" in the log reads top-to-bottom in causal order:
    [EVICT] / [WRITEBACK]   (only if the access faulted and frames were full)
    ACCESS  header          (the access being serviced)
    frames  snapshot        (state of RAM afterwards)
"""

from __future__ import annotations
from typing import Iterable

SEP = "-" * 78


class TraceLogger:
    """Writes a human-readable per-access trace to a log file."""

    def __init__(self, path: str = "trace.log") -> None:
        self._fh = open(path, "w", encoding="utf-8")
        self._n = 0
        self._w("MMU INTERNAL TRACE")
        self._w("Block order: eviction/writeback (if any) -> access -> frame snapshot")
        self._w("Routing shown as L1[i] -> L2[j] through the multi-level page table")
        self._w(SEP)

    # ------------------------------------------------------------------
    def _w(self, line: str = "") -> None:
        self._fh.write(line + "\n")

    # ------------------------------------------------------------------
    #  Eviction (logged from _evict_or_get_free, i.e. just before the
    #  access header of the access that triggered it).
    # ------------------------------------------------------------------
    def log_eviction(
        self,
        victim_file:   str,
        victim_vpn:    int,
        victim_frame:  int,
        was_dirty:     bool,
        incoming_file: str,
        incoming_vpn:  int,
    ) -> None:
        self._w(
            f"[EVICT]     LRU victim {victim_file} vpn={victim_vpn} "
            f"(frame {victim_frame}, dirty={was_dirty})  "
            f"-> freeing for {incoming_file} vpn={incoming_vpn}"
        )

    # ------------------------------------------------------------------
    #  Writeback (dirty victim flushed to disk before its frame is reused).
    # ------------------------------------------------------------------
    def log_writeback(self, file_id: str, vpn: int, frame_idx: int) -> None:
        self._w(
            f"[WRITEBACK] {file_id} vpn={vpn} (frame {frame_idx}) flushed to disk"
        )

    # ------------------------------------------------------------------
    #  Access header.
    # ------------------------------------------------------------------
    def log_access(
        self,
        file_id:     str,
        vpn:         int,
        op:          str,
        l1_idx:      int,
        l2_idx:      int,
        resolution:  str,
        frame_idx:   int,
        dirty_after: bool,
    ) -> None:
        self._n += 1
        self._w(f"ACCESS #{self._n:<3} {op:<5} {file_id:<16} vpn={vpn}")
        self._w(f"            route : L1[{l1_idx}] -> L2[{l2_idx}]")
        self._w(
            f"            result: {resolution:<10} frame {frame_idx}  "
            f"dirty={dirty_after}"
        )

    # ------------------------------------------------------------------
    #  Frame snapshot — closes the access block with a separator.
    #  Reads the _snap_* attributes the MMU stamps onto each Frame.
    # ------------------------------------------------------------------
    def log_frame_snapshot(self, frames: Iterable) -> None:
        self._w("            frames:")
        for f in frames:
            if not f.in_use:
                self._w(f"              [{f.idx}] free")
            elif hasattr(f, "_snap_file"):
                self._w(
                    f"              [{f.idx}] {f._snap_file} "
                    f"vpn={f._snap_vpn} dirty={f._snap_dirty}"
                )
            else:
                self._w(f"              [{f.idx}] occupied (no PTE)")
        self._w(SEP)

    # ------------------------------------------------------------------
    #  Final summary line at close().
    # ------------------------------------------------------------------
    def log_final(self, stats: dict) -> None:
        self._w("TRACE COMPLETE -- final statistics")
        for k, v in stats.items():
            self._w(f"   {k:<12}: {v}")
        self._w(SEP)

    def close(self) -> None:
        self._fh.flush()
        self._fh.close()