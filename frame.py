from constants import PAGE_SIZE

class Frame:
    def __init__(self, idx: int):
        self.idx = idx                    # Frame number
        self.data = b'\0' * PAGE_SIZE     # Raw data only
        self.p_file = None                # Reference to file (needed for writeback)

    def clear(self):
        """Clear frame data when evicted"""
        self.data = b'\0' * PAGE_SIZE
        self.p_file = None