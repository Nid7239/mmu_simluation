import os
from constants import PAGE_SIZE

class PhysicalFile:
    def __init__(self, filename: str):
        self.file_id = filename
        self.path = filename
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"File '{self.path}' not found.")
        self.size = os.path.getsize(self.path)
        self.num_pages = (self.size + PAGE_SIZE - 1) // PAGE_SIZE

    def read_page(self, page_idx: int) -> bytes:
        if page_idx >= self.num_pages:
            raise IndexError(f"Page {page_idx} out of range.")
        offset = page_idx * PAGE_SIZE
        with open(self.path, "rb") as f:
            f.seek(offset)
            return f.read(PAGE_SIZE).ljust(PAGE_SIZE, b'\0')

    def write_page(self, page_idx: int, data: bytes):
        if page_idx >= self.num_pages:
            raise IndexError(f"Page {page_idx} out of range.")
        offset = page_idx * PAGE_SIZE
        padded = data.ljust(PAGE_SIZE, b'\0')[:PAGE_SIZE]
        with open(self.path, "r+b") as f:
            f.seek(offset)
            f.write(padded)