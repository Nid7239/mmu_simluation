class Frame:
    def __init__(self, idx: int):
        self.idx = idx
        self.page = None       # String label (e.g., "inventory.db_p0")
        self.data = None       # Holds the byte data or clean text string
        self.dirty = False     # Flips to True when a WRITE operation occurs
        self.p_file = None     # Reference to the PhysicalFile object for write-backs

    def clear(self):
        """Resets the physical frame slot to an empty state."""
        self.page = None
        self.data = None
        self.dirty = False
        self.p_file = None