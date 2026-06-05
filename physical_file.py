"""
physical_file.py
================
Represents a file on disk as an addressable sequence of fixed-size pages.

PhysicalFile is the MMU's view of the storage layer.  It exposes
read_page() and write_page() so the MMU can load pages into frames on a
fault and flush dirty pages on eviction — without knowing anything about
the underlying filesystem.
"""

from __future__ import annotations
import os
from constants import PAGE_SIZE


class PhysicalFile:
    """An on-disk file accessed one page at a time."""

    def __init__(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath!r}")

        self.file_id:  str = filepath          # unique identifier used as a key
        self.path:     str = os.path.abspath(filepath)
        self.size:     int = os.path.getsize(filepath)
        self.num_pages: int = max(1, (self.size + PAGE_SIZE - 1) // PAGE_SIZE)

    # ------------------------------------------------------------------

    def read_page(self, page_idx: int) -> bytes:
        """Read and return one page of raw bytes from disk."""
        if page_idx >= self.num_pages:
            raise IndexError(
                f"Page {page_idx} out of range "
                f"(file {self.file_id!r} has {self.num_pages} pages)."
            )
        with open(self.path, "rb") as fh:
            fh.seek(page_idx * PAGE_SIZE)
            return fh.read(PAGE_SIZE).ljust(PAGE_SIZE, b'\x00')

    def write_page(self, page_idx: int, data: bytes) -> None:
        """Write one page of raw bytes back to disk (writeback on eviction)."""
        if page_idx >= self.num_pages:
            raise IndexError(
                f"Page {page_idx} out of range "
                f"(file {self.file_id!r} has {self.num_pages} pages)."
            )
        padded = data[:PAGE_SIZE].ljust(PAGE_SIZE, b'\x00')
        with open(self.path, "r+b") as fh:
            fh.seek(page_idx * PAGE_SIZE)
            fh.write(padded)

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PhysicalFile({self.file_id!r}, pages={self.num_pages})"
