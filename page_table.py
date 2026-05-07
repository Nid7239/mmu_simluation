from constants import PAGE_TABLE_LIMIT


class Entry:
    def __init__(self, frame, timestamp):
        self.frame = frame
        self.last_access = timestamp    # Updated on every access (hit or miss)
        self.valid = True               # False = soft-invalidated (e.g. pending eviction)


class PageTable:
    def __init__(self):
        # Two-level directory:  file_id  ->  { page_idx: Entry }
        self.directory: dict[str, dict[int, Entry]] = {}
        self._total_mapped = 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, file_id: str, page_idx: int) -> Entry | None:
        """Return the Entry if the page is mapped and valid, otherwise None."""
        entry = self.directory.get(file_id, {}).get(page_idx)
        if entry and entry.valid:
            return entry
        return None

    @property
    def total_mapped(self) -> int:
        return self._total_mapped

    def is_full(self) -> bool:
        return self._total_mapped >= PAGE_TABLE_LIMIT

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def map(self, file_id: str, page_idx: int, frame, timestamp) -> None:
        """Insert or update a page→frame mapping.

        Raises RuntimeError if PAGE_TABLE_LIMIT would be exceeded on a new mapping.
        """
        is_new = self.get(file_id, page_idx) is None
        if is_new and self.is_full():
            raise RuntimeError(
                f"Page table full ({PAGE_TABLE_LIMIT} entries). "
                "Cannot map {file_id} page {page_idx}."
            )
        if file_id not in self.directory:
            self.directory[file_id] = {}
        self.directory[file_id][page_idx] = Entry(frame, timestamp)
        if is_new:
            self._total_mapped += 1

    def update_access(self, file_id: str, page_idx: int, timestamp) -> None:
        """Refresh last_access on a cache hit."""
        entry = self.directory.get(file_id, {}).get(page_idx)
        if entry:
            entry.last_access = timestamp

    def unmap(self, file_id: str, page_idx: int) -> None:
        """Remove a mapping and clear its frame."""
        l2 = self.directory.get(file_id)
        if l2 and page_idx in l2:
            entry = l2[page_idx]
            entry.valid = False
            if entry.frame:
                entry.frame.clear()
            del l2[page_idx]
            self._total_mapped -= 1
            if not l2:
                del self.directory[file_id]

    def soft_invalidate(self, file_id: str, page_idx: int) -> None:
        """Mark a page as invalid without immediately freeing the frame.

        Useful for simulating dirty-page eviction where the write-back
        happens asynchronously.
        """
        entry = self.directory.get(file_id, {}).get(page_idx)
        if entry:
            entry.valid = False
