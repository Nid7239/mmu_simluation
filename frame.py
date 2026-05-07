class Frame:
    def __init__(self, idx):
        self.idx      = idx
        self.page     = None   # Label: "<file_id>_p<page_idx>"
        self.data     = None   # Raw bytes loaded from disk
        self.dirty    = False  # True if written but not flushed to disk
        self.p_file   = None   # Back-reference to PhysicalFile — enables cross-file write-back

    def clear(self):
        self.page   = None
        self.data   = None
        self.dirty  = False
        self.p_file = None

    def __repr__(self):
        preview    = f"{self.data}"[:15] + "..." if self.data else "None"
        dirty_flag = " [DIRTY]" if self.dirty else ""
        return f"Frame {self.idx}: {str(self.page):<20} | Content: {preview}{dirty_flag}"
