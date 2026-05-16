class Entry:
    def __init__(self, frame_idx: int, timestamp):
        self.frame_idx = frame_idx
        self.last_access = timestamp
        self.valid = True

class PageTable:
    def __init__(self):
        self.directory: dict[str, dict[int, Entry]] = {}
        self._total_mapped = 0

    def get(self, file_id: str, page_idx: int) -> Entry | None:
        l2 = self.directory.get(file_id)
        if l2:
            entry = l2.get(page_idx)
            if entry and entry.valid:
                return entry
        return None

    def map(self, file_id: str, page_idx: int, frame_idx: int, timestamp) -> None:
        if file_id not in self.directory:
            self.directory[file_id] = {}
        
        if page_idx not in self.directory[file_id]:
            self._total_mapped += 1
            
        self.directory[file_id][page_idx] = Entry(frame_idx, timestamp)

    def unmap(self, file_id: str, page_idx: int) -> None:
        if file_id in self.directory and page_idx in self.directory[file_id]:
            del self.directory[file_id][page_idx]
            self._total_mapped -= 1