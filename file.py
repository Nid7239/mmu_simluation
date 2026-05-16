import os
from constants import PAGE_SIZE

class PhysicalFile:
    def __init__(self, file_id: str, num_pages: int):
        self.file_id = file_id
        self.num_pages = num_pages
        self.size = num_pages * PAGE_SIZE
        self.path = f"mock_disk_{file_id}"
        self._setup_mock_file()

    def _setup_mock_file(self):
        """Creates dummy file blocks on the disk for testing read/write runs."""
        if not os.path.exists(self.path):
            with open(self.path, "wb") as f:
                # Fill the file with repeating pattern data based on its ID
                char = self.file_id[0].encode('utf-8')
                f.write(char * self.size)

    def read_page(self, page_idx: int) -> bytes:
        """Reads a specific page block from the backing store file."""
        if page_idx >= self.num_pages:
            raise IndexError("Virtual page index out of range for current file scope.")
        
        offset = page_idx * PAGE_SIZE
        with open(self.path, "rb") as f:
            f.seek(offset)
            return f.read(PAGE_SIZE)

    def write_page(self, page_idx: int, data: bytes):
        """Persists a dirty RAM page block block back onto the backing store file."""
        if page_idx >= self.num_pages:
            raise IndexError("Virtual page index out of range for current file scope.")
            
        offset = page_idx * PAGE_SIZE
        # Ensure block alignment parameters stay perfectly safe
        padded_data = data.ljust(PAGE_SIZE, b'_')[:PAGE_SIZE]
        
        with open(self.path, "r+b") as f:
            f.seek(offset)
            f.write(padded_data)