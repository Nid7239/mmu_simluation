from datetime import datetime
from frame import Frame
from page_table import PageTable
from constants import NUM_FRAMES

class _Node:
    """ Doubly Linked List."""
    __slots__ = ("file_id", "page_idx", "frame_idx", "prev", "next")
    def __init__(self, file_id: str, page_idx: int, frame_idx: int):
        self.file_id = file_id
        self.page_idx = page_idx
        self.frame_idx = frame_idx
        self.prev = self.next = None

class MMU:
    def __init__(self, n: int = NUM_FRAMES):
        # Hardware setup
        self.frames = [Frame(i) for i in range(n)]
        self.table = PageTable()
        self._tlb: dict[tuple[str, int], int] = {} 
        self.TLB_SIZE = 4
        
        # LRU management structures
        self._head = self._tail = None
        self._node_map: dict[tuple[str, int], _Node] = {}  #a hashmap (dictionary)used to quickly track: LRU linked-list nodes
        
        # Statistics for main.py logging
        self.hits = 0
        self.faults = 0
        self.tlb_hits = 0
        self.tlb_misses = 0
        self.writebacks = 0

    def access(self, p_file, page_idx: int, write_data: bytes = None):
        """The main entry point for reading or writing memory pages."""
        key = (p_file.file_id, page_idx)
        now = datetime.now() # Required by PageTable.map()
        status = ""

        # 1. TLB LOOKUP (Fastest check)
        if key in self._tlb:
            self.tlb_hits += 1
            self.hits += 1
            f_idx = self._tlb[key]
            status = "TLB_HIT"

        # 2. PAGE TABLE LOOKUP (Check if already in RAM)
        else:
            self.tlb_misses += 1
            entry = self.table.get(p_file.file_id, page_idx)
            if entry:
                self.hits += 1
                f_idx = entry.frame_idx  #takes RAM frame location from the page table entry
                self._tlb_insert(key, f_idx)
                status = "HIT"
            
            # 3. PAGE FAULT (Fetch from physical disk)
            else:
                self.faults += 1
                frame = self._get_evicted_or_free_frame()
                
                # Fetch data from file
                frame.data = p_file.read_page(page_idx)
                frame.page = f"{p_file.file_id}_p{page_idx}"
                frame.p_file = p_file
                frame.dirty = False
                
                f_idx = frame.idx
                # Update records in page
                self.table.map(p_file.file_id, page_idx, f_idx, now)
                self._tlb_insert(key, f_idx)
                
                # Register in LRU tracking
                new_node = _Node(p_file.file_id, page_idx, f_idx)
                self._node_map[key] = new_node
                self._append_tail(new_node)
                status = "FAULT"

        # FINAL ACTIONS: Move to back of LRU and handle modification
        # function unlinks its node from the middle of the linked list and snaps it straight onto the Tail.
        frame = self.frames[f_idx]
        self._update_lru(key)
        
        if write_data:
            frame.data = write_data
            frame.dirty = True

        return status, frame.data

    def _get_evicted_or_free_frame(self) -> Frame:
        """Finds an empty frame or evicts the Least Recently Used one."""
        # Check for empty slots first
        for f in self.frames:
            if f.page is None:
                return f

        # Perform Eviction (LRU)
        victim_node = self._head
        victim_key = (victim_node.file_id, victim_node.page_idx)
        frame = self.frames[victim_node.frame_idx]

        # Write-back if data was modified while in RAM
        if frame.dirty and frame.p_file:
            self.writebacks += 1
            frame.p_file.write_page(victim_node.page_idx, frame.data)

        # Remove all references to the evicted page
        self._tlb.pop(victim_key, None)
        self.table.unmap(victim_node.file_id, victim_node.page_idx)
        self._remove_node(victim_node)
        del self._node_map[victim_key]
        
        frame.clear()
        return frame

    def _update_lru(self, key):
        """Moves a recently accessed page to the end (most recent) of the list."""
        node = self._node_map.get(key)
        if node:
            self._remove_node(node)
            self._append_tail(node)

    def _tlb_insert(self, key, f_idx):
        """Adds a page to the TLB."""
        if len(self._tlb) >= self.TLB_SIZE:
            oldest = next(iter(self._tlb))
            del self._tlb[oldest]
        self._tlb[key] = f_idx

    def _remove_node(self, node):
        """Removes a node from the doubly linked list."""
        if node.prev: node.prev.next = node.next
        else: self._head = node.next
        if node.next: node.next.prev = node.prev
        else: self._tail = node.prev
        node.next = node.prev = None

    def _append_tail(self, node):
        """Adds a node to the end of the doubly linked list."""
        if not self._tail:
            self._head = self._tail = node
        else:
            self._tail.next = node
            node.prev = self._tail
            self._tail = node

    def dump_state(self, accessed_file_id: str = "") -> str:
        """Formatted visualization for the simulation logs."""
        W = 76
        def row(*cols, widths):
            cells = "  ".join(f"{str(c):<{w}}" for c, w in zip(cols, widths))
            return f"  ║  {cells}  ║"

        out = ["", "  ┌" + "─" * W + "┐", "  │" + "MMU HARDWARE SNAPSHOT".center(W) + "│", "  └" + "─" * W + "┘"]
        out.append(f"\n  TLB ({len(self._tlb)}/{self.TLB_SIZE})")
        out.append(row("PAGE KEY", "FRAME", "STATUS", widths=[30, 10, 10]))
        for (fid, pidx), fidx in self._tlb.items():
            out.append(row(f"{fid} P{pidx}", f"F{fidx}", "VALID", widths=[30, 10, 10]))

        out.append("\n  PHYSICAL RAM")
        out.append(row("FRAME", "PAGE LABEL", "DIRTY", widths=[10, 30, 10]))
        for fr in self.frames:
            label = fr.page if fr.page else "FREE"
            dirty = "YES" if fr.dirty else "NO"
            out.append(row(f"F{fr.idx}", label, dirty, widths=[10, 30, 10]))

        out.append("\n  STATISTICS")
        out.append(row("HITS", "FAULTS", "TLB_HITS", "WR-BACKS", widths=[10, 10, 10, 10]))
        out.append(row(self.hits, self.faults, self.tlb_hits, self.writebacks, widths=[10, 10, 10, 10]))
        
        return "\n".join(out) + "\n"