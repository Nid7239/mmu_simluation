import os
from constants import PAGE_SIZE
class PhysicalFile:
    def __init__(self, path, num_pages: int = 4):
        self.path = path

        # Remove old file if exists
        if os.path.exists(path):
            os.remove(path)
        with open(path, "wb") as f:
            f.write(os.urandom(num_pages * PAGE_SIZE))
        self.file_id   = os.path.basename(path)
        self.size      = os.path.getsize(path)
        self.num_pages = (self.size + PAGE_SIZE - 1) // PAGE_SIZE
    def read_page(self, page_idx: int) -> bytes:
        if page_idx < 0 or page_idx >= self.num_pages:
            raise IndexError(
                f"Page {page_idx} out of range for '{self.file_id}' "
                f"({self.num_pages} pages total)"
            )
        with open(self.path, "rb") as f:
            f.seek(page_idx * PAGE_SIZE)
            return f.read(PAGE_SIZE)

    def write_page(self, page_idx: int, data: bytes) -> None:
        if page_idx < 0 or page_idx >= self.num_pages:
            raise IndexError(f"Page {page_idx} out of range for '{self.file_id}'")
        padded = data.ljust(PAGE_SIZE, b"\x00")[:PAGE_SIZE]
        with open(self.path, "r+b") as f:
            f.seek(page_idx * PAGE_SIZE)
            f.write(padded)
