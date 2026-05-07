from datetime import datetime
from frame import Frame
from page_table import PageTable
from constants import NUM_FRAMES


# ---------------------------------------------------------------------------
# LRU doubly-linked list node
# ---------------------------------------------------------------------------

class _Node:
    __slots__ = ("file_id", "page_idx", "prev", "next")
    def __init__(self, file_id: str, page_idx: int):
        self.file_id  = file_id
        self.page_idx = page_idx
        self.prev = self.next = None


# ---------------------------------------------------------------------------
# MMU  (TLB → Page Table → Disk)
# ---------------------------------------------------------------------------

class MMU:
    def __init__(self, n: int = NUM_FRAMES):
        self.frames    = [Frame(i) for i in range(n)]
        self.table     = PageTable()

        # TLB — small fast-path cache: (file_id, page_idx) -> Frame
        # Checked before the page table on every access
        self._tlb: dict[tuple[str, int], Frame] = {}
        self.TLB_SIZE = 8   # typical real TLBs: 8–2048 entries

        # LRU list: head = least-recently-used, tail = most-recently-used
        self._head = self._tail = None
        self._node_map: dict[tuple[str, int], _Node] = {}

        # Session counters
        self.hits         = 0
        self.faults       = 0
        self.tlb_hits     = 0
        self.tlb_misses   = 0
        self.writebacks   = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def access(self, p_file, page_idx: int, write_data: bytes | None = None):
        """Read (or write) a page.

        Lookup order:
          1. TLB  (fastest — direct frame reference)
          2. Page table  (slower — two-level directory lookup)
          3. Disk  (slowest — page fault, load from file)

        Returns (status, data) where status is one of:
          "TLB_HIT"   — served from TLB
          "HIT"       — served from page table (TLB miss, RAM hit)
          "FAULT"     — loaded from disk
        """
        key = (p_file.file_id, page_idx)
        now = datetime.now()

        # ── 1. TLB lookup ────────────────────────────────────────────────
        if key in self._tlb:
            self.tlb_hits += 1
            self.hits     += 1
            frame = self._tlb[key]
            self.table.update_access(p_file.file_id, page_idx, now)
            self._move_to_tail(self._node_map[key])
            if write_data is not None:
                frame.data  = write_data
                frame.dirty = True
            return "TLB_HIT", frame.data

        # ── 2. Page table lookup ─────────────────────────────────────────
        self.tlb_misses += 1
        entry = self.table.get(p_file.file_id, page_idx)

        if entry:
            self.hits += 1
            self.table.update_access(p_file.file_id, page_idx, now)
            self._move_to_tail(self._node_map[key])
            self._tlb_insert(key, entry.frame)   # promote to TLB
            if write_data is not None:
                entry.frame.data  = write_data
                entry.frame.dirty = True
            return "HIT", entry.frame.data

        # ── 3. Page fault — load from disk ───────────────────────────────
        self.faults  += 1
        free_frame    = self._get_free_frame()

        data               = p_file.read_page(page_idx)
        free_frame.page    = f"{p_file.file_id}_p{page_idx}"
        free_frame.data    = data
        free_frame.dirty   = False
        free_frame.p_file  = p_file           # store back-reference

        if write_data is not None:
            free_frame.data  = write_data
            free_frame.dirty = True

        self.table.map(p_file.file_id, page_idx, free_frame, now)
        self._tlb_insert(key, free_frame)     # add to TLB

        new_node = _Node(p_file.file_id, page_idx)
        self._node_map[key] = new_node
        self._append_tail(new_node)

        return "FAULT", free_frame.data

    # ------------------------------------------------------------------
    # TLB helpers
    # ------------------------------------------------------------------

    def _tlb_insert(self, key: tuple, frame: Frame) -> None:
        """Insert into TLB, evicting the oldest entry when full (FIFO)."""
        if len(self._tlb) >= self.TLB_SIZE and key not in self._tlb:
            oldest = next(iter(self._tlb))
            del self._tlb[oldest]
        self._tlb[key] = frame

    def _tlb_invalidate(self, key: tuple) -> None:
        """Remove a mapping from the TLB (called on page eviction)."""
        self._tlb.pop(key, None)

    # ------------------------------------------------------------------
    # Frame / eviction helpers
    # ------------------------------------------------------------------

    def _get_free_frame(self) -> Frame:
        """Return a free frame, evicting the LRU page when RAM is full."""
        free = next((f for f in self.frames if f.page is None), None)
        if free:
            return free

        # Evict LRU victim
        victim       = self._head
        victim_key   = (victim.file_id, victim.page_idx)
        victim_frame = next(
            f for f in self.frames
            if f.page == f"{victim.file_id}_p{victim.page_idx}"
        )

        # Write-back if dirty — works for ANY file via the stored back-reference
        if victim_frame.dirty and victim_frame.p_file is not None:
            self.writebacks += 1
            victim_frame.p_file.write_page(victim.page_idx, victim_frame.data)

        # Invalidate TLB entry for the evicted page
        self._tlb_invalidate(victim_key)

        # Remove from page table (also calls frame.clear())
        self.table.unmap(victim.file_id, victim.page_idx)

        # Remove from LRU list
        del self._node_map[victim_key]
        self._head = victim.next
        if self._head: self._head.prev = None
        else:          self._tail = None

        return victim_frame

    def _append_tail(self, node: _Node) -> None:
        if self._tail is None:
            self._head = self._tail = node
        else:
            node.prev       = self._tail
            self._tail.next = node
            self._tail      = node

    def _move_to_tail(self, node: _Node) -> None:
        if node is self._tail: return
        if node.prev: node.prev.next = node.next
        else:         self._head = node.next
        if node.next: node.next.prev = node.prev
        node.prev = self._tail
        node.next = None
        if self._tail: self._tail.next = node
        self._tail = node

    # ------------------------------------------------------------------
    # Professional snapshot output
    # ------------------------------------------------------------------

    def dump_state(self, accessed_file_id: str = "") -> str:
        W = 76

        def top(title):
            return f"  ╔══ {title} {'═' * (W - len(title) - 4)}╗"

        def row(*cols, widths):
            cells = "  ".join(f"{str(c):<{w}}" for c, w in zip(cols, widths))
            return f"  ║  {cells}  ║"

        def sep():
            return f"  ╟{'─' * W}╢"

        def lbl(text):
            return f"  ║  {text:<{W - 2}}║"

        def end():
            return f"  ╚{'═' * W}╝"

        out = []
        out.append("")
        out.append("  ┌" + "─" * W + "┐")
        out.append("  │" + "  MMU  ·  HARDWARE SNAPSHOT".center(W) + "│")
        out.append("  └" + "─" * W + "┘")

        # ── 1. TLB ───────────────────────────────────────────────────────
        out.append("")
        out.append(top(f"TLB  ({len(self._tlb)}/{self.TLB_SIZE} entries)"))
        out.append(row("PAGE KEY", "FRAME", "DIRTY",
                       widths=[30, 8, 8]))
        out.append(sep())
        if not self._tlb:
            out.append(lbl("  (empty)"))
        else:
            for (fid, pidx), fr in self._tlb.items():
                dirty = "YES ✗" if fr.dirty else "NO  ✓"
                out.append(row(f"{fid} · P{pidx}", f"F{fr.idx}", dirty,
                               widths=[30, 8, 8]))
        out.append(end())

        # ── 2. Physical Frames ───────────────────────────────────────────
        out.append("")
        out.append(top("PHYSICAL FRAMES"))
        out.append(row("FRAME", "PAGE LABEL", "DATA (hex)", "DIRTY", "STATUS",
                       widths=[6, 24, 22, 8, 7]))
        out.append(sep())
        for fr in self.frames:
            if fr.page is None:
                out.append(row("F"+str(fr.idx), "—", "—", "—", "FREE",
                               widths=[6, 24, 22, 8, 7]))
            else:
                raw     = fr.data.hex(" ") if fr.data else "—"
                preview = raw[:22]
                dirty   = "YES ✗" if fr.dirty else "NO  ✓"
                out.append(row("F"+str(fr.idx), fr.page, preview, dirty, "LOADED",
                               widths=[6, 24, 22, 8, 7]))
        out.append(end())

        # ── 3. Per-File Page Tables ──────────────────────────────────────
        out.append("")
        out.append(top("PAGE TABLES  (one table per file)"))
        all_files = list(self.table.directory.keys())
        if not all_files:
            out.append(lbl("  (no pages mapped yet)"))
        else:
            for i, file_id in enumerate(all_files):
                page_map = self.table.directory[file_id]
                tag = "  ◀ LAST ACCESSED" if file_id == accessed_file_id else ""
                out.append(lbl(f"  FILE : {file_id}{tag}"))
                out.append(sep())
                out.append(row("PAGE", "FRAME", "VALID", "DIRTY", "LAST ACCESS",
                               widths=[6, 7, 7, 8, 30]))
                out.append(sep())
                for page_idx in sorted(page_map.keys()):
                    entry = page_map[page_idx]
                    fr    = entry.frame
                    valid = "YES" if entry.valid else "NO"
                    dirty = "YES ✗" if fr.dirty else "NO  ✓"
                    ts    = entry.last_access.strftime("%Y-%m-%d %H:%M:%S.%f")
                    out.append(row(f"P{page_idx}", f"F{fr.idx}", valid, dirty, ts,
                                   widths=[6, 7, 7, 8, 30]))
                if i < len(all_files) - 1:
                    out.append(sep())
                    out.append(lbl(""))
        out.append(end())

        # ── 4. LRU Queue ────────────────────────────────────────────────
        out.append("")
        out.append(top("LRU EVICTION QUEUE   [ left = next victim ]"))
        curr, nodes = self._head, []
        while curr:
            nodes.append(f"({curr.file_id} · P{curr.page_idx})")
            curr = curr.next
        queue = "  →  ".join(nodes) if nodes else "— empty —"
        out.append(lbl("  " + queue))
        out.append(end())

        # ── 5. Session Statistics ────────────────────────────────────────
        out.append("")
        out.append(top("SESSION STATISTICS"))
        total     = max(1, self.hits + self.faults)
        tlb_total = max(1, self.tlb_hits + self.tlb_misses)
        out.append(row("HITS", "FAULTS", "TLB HITS", "WR-BACKS", "HIT RATE", "TLB RATE",
                       widths=[7, 7, 9, 9, 10, 10]))
        out.append(sep())
        out.append(row(
            self.hits, self.faults, self.tlb_hits, self.writebacks,
            f"{self.hits/total:.1%}",
            f"{self.tlb_hits/tlb_total:.1%}",
            widths=[7, 7, 9, 9, 10, 10],
        ))
        out.append(end())
        out.append("")

        return "\n".join(out) + "\n"
