
from __future__ import annotations
import sys
from datetime import datetime
from typing import Optional

from constants import NUM_FRAMES, TLB_SIZE
from frame import Frame
from page_directory import PageDirectory
from page_table_entry import PageTableEntry
from physical_file import PhysicalFile
from lru_bst import LRUBST
from trace_logger import TraceLogger

VPNKey = tuple[str, int]   # (file_id, vpn)


class MMU:
    """
    Simulated Memory Management Unit.

    Parameters
    ----------
    num_frames : Number of physical frames in simulated RAM.
    log_path   : Destination for the high-level simulation log.
    trace      : When True, a detailed per-access trace is written to
                 trace_path in addition to the summary log.
    trace_path : Destination for the step-by-step internal trace log.
    """

    def __init__(
        self,
        num_frames: int = NUM_FRAMES,
        log_path:   str = "output.log",
        trace:      bool = False,
        trace_path: str  = "trace.log",
    ) -> None:
        self.frames:         list[Frame]        = [Frame(i) for i in range(num_frames)]
        self.page_directory: PageDirectory      = PageDirectory()
        self.tlb:            dict[VPNKey, int]  = {}
        self.lru:            LRUBST             = LRUBST()
        self._frame_to_key:  dict[int, VPNKey]  = {}

        self.stats: dict[str, int] = {
            "hits":       0,
            "faults":     0,
            "tlb_hits":   0,
            "tlb_misses": 0,
            "writebacks": 0,
        }

        self._log_file = open(log_path, "w", encoding="utf-8")
        sys.stdout = self._log_file

        self._tracer: Optional[TraceLogger] = TraceLogger(trace_path) if trace else None

    # ------------------------------------------------------------------
    #  Public: translate and access a virtual page
    # ------------------------------------------------------------------

    def access(
        self,
        p_file:     PhysicalFile,
        vpn:        int,
        write_data: Optional[bytes] = None,
    ) -> bytes:
        """
        Access virtual page *vpn* of *p_file*.

        Parameters
        ----------
        p_file     : The file being accessed.
        vpn        : Virtual page number within that file.
        write_data : If provided, overwrite the page with this data
                     and mark the entry dirty.

        Returns
        -------
        bytes : The current contents of the physical frame after access.
        """
        key: VPNKey = (p_file.file_id, vpn)
        now = datetime.now()

        frame_idx, resolution = self._translate(p_file, key, vpn, now)

        # Write path — update frame data and mark the page dirty
        if write_data is not None:
            self.frames[frame_idx].load(write_data)
            entry = self.page_directory.get(p_file.file_id, vpn)
            if entry is not None:
                entry.dirty = True

        # Keep the LRU tracker in sync on every access
        self.lru.touch(key, now)

        # Emit a trace record if tracing is enabled
        if self._tracer is not None:
            l1_idx, l2_idx = self.page_directory._split_vpn(vpn)
            entry = self.page_directory.get(p_file.file_id, vpn)
            dirty_after = entry.dirty if entry else False

            self._tracer.log_access(
                file_id     = p_file.file_id,
                vpn         = vpn,
                op          = "WRITE" if write_data is not None else "READ",
                l1_idx      = l1_idx,
                l2_idx      = l2_idx,
                resolution  = resolution,
                frame_idx   = frame_idx,
                dirty_after = dirty_after,
            )
            self._attach_snap_data()
            self._tracer.log_frame_snapshot(self.frames)

        return self.frames[frame_idx].data

    # ------------------------------------------------------------------
    #  Translation (TLB → page table → page fault)
    # ------------------------------------------------------------------

    def _translate(
        self,
        p_file: PhysicalFile,
        key:    VPNKey,
        vpn:    int,
        now:    datetime,
    ) -> tuple[int, str]:
        """
        Return (frame_idx, resolution_label) for *key*.

        resolution_label is one of: "TLB_HIT", "PT_HIT", "PAGE_FAULT".
        """

        # ── TLB hit ─────────────────────────────────────────────────────
        if key in self.tlb:
            self.stats["tlb_hits"] += 1
            self.stats["hits"]     += 1
            frame_idx = self.tlb[key]
            entry = self.page_directory.get(p_file.file_id, vpn)
            if entry is not None:
                entry.touch(now)
            return frame_idx, "TLB_HIT"

        # ── TLB miss ────────────────────────────────────────────────────
        self.stats["tlb_misses"] += 1
        entry = self.page_directory.get(p_file.file_id, vpn)

        if entry is not None:
            # Page-table hit: mapping exists, just reload the TLB
            self.stats["hits"] += 1
            entry.touch(now)
            self._tlb_insert(key, entry.frame_idx)
            return entry.frame_idx, "PT_HIT"

        # ── Page fault ──────────────────────────────────────────────────
        self.stats["faults"] += 1
        frame = self._evict_or_get_free(incoming_file=p_file.file_id, incoming_vpn=vpn)

        data = p_file.read_page(vpn)
        frame.load(data)

        self.page_directory.map(p_file.file_id, vpn, frame.idx, now)
        self._tlb_insert(key, frame.idx)
        self._frame_to_key[frame.idx] = key

        return frame.idx, "PAGE_FAULT"

    # ------------------------------------------------------------------
    #  TLB management (FIFO eviction)
    # ------------------------------------------------------------------

    def _tlb_insert(self, key: VPNKey, frame_idx: int) -> None:
        """Insert *key* → *frame_idx* into the TLB, evicting the oldest entry if full."""
        if len(self.tlb) >= TLB_SIZE and key not in self.tlb:
            oldest_key = next(iter(self.tlb))
            del self.tlb[oldest_key]
        self.tlb[key] = frame_idx

    # ------------------------------------------------------------------
    #  Frame eviction
    # ------------------------------------------------------------------

    def _evict_or_get_free(
        self,
        incoming_file: str = "",
        incoming_vpn:  int = -1,
    ) -> Frame:
        """
        Return a free physical frame, evicting the LRU page if necessary.

        Steps on eviction:
          1. Identify the LRU victim from the BST.
          2. Flush the frame to disk if its page is dirty.
          3. Remove the victim's TLB entry, page table entry, and reverse-map entry.
          4. Clear and return the now-free frame.
        """
        # Fast path: a free frame is available
        for frame in self.frames:
            if not frame.in_use:
                return frame

        # Slow path: evict the least-recently-used page
        victim_key = self.lru.remove_oldest()
        if victim_key is None:
            raise RuntimeError("LRU tracker is empty but all frames are occupied.")

        v_file_id, v_vpn = victim_key
        entry = self.page_directory.get(v_file_id, v_vpn)
        if entry is None:
            raise RuntimeError(
                f"Page table entry missing for eviction candidate "
                f"({v_file_id!r}, vpn={v_vpn})."
            )

        frame = self.frames[entry.frame_idx]

        # Trace eviction before tearing it down
        if self._tracer is not None:
            self._tracer.log_eviction(
                victim_file   = v_file_id,
                victim_vpn    = v_vpn,
                victim_frame  = frame.idx,
                was_dirty     = entry.dirty,
                incoming_file = incoming_file,
                incoming_vpn  = incoming_vpn,
            )

        if entry.dirty:
            self.stats["writebacks"] += 1
            self._writeback(entry, frame)

        # Tear down all references to this mapping
        self.tlb.pop(victim_key, None)
        self._frame_to_key.pop(entry.frame_idx, None)
        self.page_directory.unmap(v_file_id, v_vpn)
        frame.clear()

        return frame

    # ------------------------------------------------------------------
    #  Writeback (dirty page → disk)
    # ------------------------------------------------------------------

    def _writeback(self, entry: PageTableEntry, frame: Frame) -> None:
        """Flush a dirty frame back to the file it was loaded from."""
        if self._tracer is not None:
            self._tracer.log_writeback(
                file_id   = entry.file_id,
                vpn       = entry.vpn,
                frame_idx = frame.idx,
            )
        try:
            pf = PhysicalFile(entry.file_id)
            pf.write_page(entry.vpn, frame.data)
        except Exception as exc:
            print(
                f"[MMU] Writeback failed for {entry.file_id!r} "
                f"vpn={entry.vpn}: {exc}",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    #  Trace helper — attach PTE snapshot data directly onto Frame objects
    #  so TraceLogger.log_frame_snapshot() can read them without importing
    #  PageDirectory.
    # ------------------------------------------------------------------

    def _attach_snap_data(self) -> None:
        """Stamp each Frame with current PTE metadata for the snapshot printer."""
        for frame in self.frames:
            entry = self._entry_for_frame(frame.idx)
            if entry is not None:
                frame._snap_file  = entry.file_id   # type: ignore[attr-defined]
                frame._snap_vpn   = entry.vpn        # type: ignore[attr-defined]
                frame._snap_dirty = entry.dirty      # type: ignore[attr-defined]
            elif hasattr(frame, "_snap_file"):
                del frame._snap_file                 # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    #  Reporting (output.log)
    # ------------------------------------------------------------------

    def dump(self) -> None:
        """Print the final simulation state to output.log."""
        sep = "=" * 80

        print(f"\n{sep}")
        print("MMU SIMULATION — FINAL STATE")
        print(sep)

        # 1. Frame table
        print("\n── FRAME TABLE " + "─" * 65)
        print(f"{'Frame':<7} {'Status':<10} {'File':<24} {'VPN':<6} {'Dirty'}")
        print("─" * 60)
        for frame in self.frames:
            if frame.in_use:
                entry = self._entry_for_frame(frame.idx)
                if entry is not None:
                    print(
                        f"{frame.idx:<7} {'occupied':<10} {entry.file_id:<24} "
                        f"{entry.vpn:<6} {entry.dirty}"
                    )
                else:
                    print(f"{frame.idx:<7} {'occupied':<10} {'(no PTE)':<24} {'?':<6} ?")
            else:
                print(f"{frame.idx:<7} {'free':<10} {'-':<24} {'-':<6} -")

        # 2. Page directory summary
        print("\n── PAGE DIRECTORY SUMMARY " + "─" * 54)
        summary = self.page_directory.get_summary()
        if not summary:
            print("  (empty)")
        for l1_idx, l2_summary in summary.items():
            for l2_idx, count in l2_summary.items():
                print(f"  L1[{l1_idx}] → L2[{l2_idx}] : {count} page(s) mapped")
        print(f"\n  Total mapped : {self.page_directory.total_mapped()} page(s)")

        # 3. TLB state
        print("\n── TLB STATE " + "─" * 67)
        if not self.tlb:
            print("  (empty)")
        for (fid, vpn), fidx in self.tlb.items():
            print(f"  ({fid}, vpn={vpn:>4})  →  frame {fidx}")

        # 4. Statistics
        print("\n── STATISTICS " + "─" * 66)
        total   = self.stats["hits"] + self.stats["faults"]
        hit_pct = (self.stats["hits"]     / total      * 100) if total      else 0.0
        tlb_tot = self.stats["tlb_hits"]  + self.stats["tlb_misses"]
        tlb_pct = (self.stats["tlb_hits"] / tlb_tot    * 100) if tlb_tot    else 0.0

        print(f"  Total accesses  : {total}")
        print(f"  Page hits       : {self.stats['hits']}")
        print(f"  Page faults     : {self.stats['faults']}")
        print(f"  Hit ratio       : {hit_pct:.1f}%")
        print(f"  TLB hits        : {self.stats['tlb_hits']}  ({tlb_pct:.1f}%)")
        print(f"  TLB misses      : {self.stats['tlb_misses']}")
        print(f"  Writebacks      : {self.stats['writebacks']}")
        print(f"  LRU tree size   : {len(self.lru)}")
        print(sep)

    def _entry_for_frame(self, frame_idx: int) -> Optional[PageTableEntry]:
        """O(1) reverse lookup: frame index → PageTableEntry via _frame_to_key."""
        key = self._frame_to_key.get(frame_idx)
        if key is None:
            return None
        file_id, vpn = key
        return self.page_directory.get(file_id, vpn)

    # ------------------------------------------------------------------
    #  Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close all log files, restoring stdout."""
        if self._tracer is not None:
            self._tracer.log_final(self.stats)
            self._tracer.close()
        self._log_file.flush()
        self._log_file.close()
        sys.stdout = sys.__stdout__