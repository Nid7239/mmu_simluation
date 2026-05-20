# physical_file.py
import os

class PhysicalFile:
    def __init__(self, filepath: str, page_size: int = 4096, total_pages: int = 10):
        self.file_id = os.path.basename(filepath)
        self.filepath = filepath
        self.page_size = page_size
        self.total_size = page_size * total_pages
        
        # Ensure the file exists on the physical storage device pre-filled with zeroed-out blocks
        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(b"\0" * self.total_size)

    def read_page_data(self, page_idx: int) -> bytes:
        """Native implementation: jumps directly to the byte offset and extracts a 4KB chunk."""
        offset = page_idx * self.page_size
        with open(self.filepath, "rb") as f:
            f.seek(offset)
            return f.read(self.page_size)

    def write_page_data(self, page_idx: int, data_bytes: bytes):
        """Native implementation: shifts to the specific offset and safely modifies the file contents."""
        offset = page_idx * self.page_size
        cleaned_data = data_bytes.ljust(self.page_size, b'\0')[:self.page_size]
        with open(self.filepath, "r+b") as f:
            f.seek(offset)
            f.write(cleaned_data)