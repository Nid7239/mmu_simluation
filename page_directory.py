from page_table import PageTable

class PageDirectory:
    def __init__(self):
        self.page_tables = {}   # table_idx -> PageTable

    def get(self, table_idx, page_idx):
        if table_idx not in self.page_tables:
            return None
        return self.page_tables[table_idx].get(page_idx)

    def map(self, table_idx, page_idx, frame_idx, timestamp):
        if table_idx not in self.page_tables:
            self.page_tables[table_idx] = PageTable()
        self.page_tables[table_idx].map(page_idx, frame_idx, timestamp)

    def unmap(self, table_idx, page_idx):
        if table_idx in self.page_tables:
            self.page_tables[table_idx].unmap(page_idx)
            if not self.page_tables[table_idx].entries:
                del self.page_tables[table_idx]

    def get_summary(self):
        return {idx: len(pt.entries) for idx, pt in self.page_tables.items()}