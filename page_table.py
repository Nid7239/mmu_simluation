class PageTableEntry:
    def __init__(self, frame_idx: int):
        self.frame_idx = frame_idx  # Points to the index in physical RAM

class PageTable:
    def __init__(self):
        # Explicit 2-Level Structure
        # Format: { file_id : { outer_directory_idx : { inner_page_idx : PageTableEntry } } }
        self.outer_page_directory = {}

    def _split_page(self, page_idx: int) -> tuple[int, int]:
        """Splits a flat page number into an Outer and Inner index row."""
        outer_idx = page_idx // 2
        inner_idx = page_idx % 2
        return outer_idx, inner_idx

    def get(self, file_id: str, page_idx: int) -> PageTableEntry:
        """Traverses the 2 levels to find an entry. Returns None if it's a Miss."""
        outer_idx, inner_idx = self._split_page(page_idx)
        
        if file_id in self.outer_page_directory:
            outer_dir = self.outer_page_directory[file_id]
            if outer_idx in outer_dir:
                inner_table = outer_dir[outer_idx]
                if inner_idx in inner_table:
                    return inner_table[inner_idx]
        return None

    def map(self, file_id: str, page_idx: int, frame_idx: int, timestamp=None):
        """Creates or updates the multi-level pathway to assign a page to a RAM frame slot."""
        outer_idx, inner_idx = self._split_page(page_idx)
        
        if file_id not in self.outer_page_directory:
            self.outer_page_directory[file_id] = {}
        if outer_idx not in self.outer_page_directory[file_id]:
            self.outer_page_directory[file_id][outer_idx] = {}
            
        self.outer_page_directory[file_id][outer_idx][inner_idx] = PageTableEntry(frame_idx)

    def unmap(self, file_id: str, page_idx: int):
        """Removes an old entry path when a page gets evicted from memory."""
        outer_idx, inner_idx = self._split_page(page_idx)
        
        if file_id in self.outer_page_directory:
            if outer_idx in self.outer_page_directory[file_id]:
                self.outer_page_directory[file_id][outer_idx].pop(inner_idx, None)