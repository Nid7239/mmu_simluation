# physical_file.py
import os
from constants import PAGE_SIZE, TOTAL_PAGES

class PhysicalFile:
    def __init__(self, filepath: str):
        self.file_id = os.path.basename(filepath)
        self.filepath = filepath
        self.page_size = PAGE_SIZE
        self.total_size = PAGE_SIZE * TOTAL_PAGES
        
        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(b"\0" * self.total_size)

    def read_page_data(self, page_idx: int) -> bytes:
        offset = page_idx * self.page_size
        with open(self.filepath, "rb") as f:
            f.seek(offset)
            return f.read(self.page_size)

    def write_page_data(self, page_idx: int, data_bytes: bytes):
        offset = page_idx * self.page_size
        cleaned_data = data_bytes.ljust(self.page_size, b'\0')[:self.page_size]
        with open(self.filepath, "r+b") as f:
            f.seek(offset)
            f.write(cleaned_data)