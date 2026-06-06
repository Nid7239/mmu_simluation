
# Physical memory
PAGE_SIZE  = 64    # bytes per page / frame
NUM_FRAMES =4   # total physical frames in simulated RAM

# TLB
TLB_SIZE = 8       # maximum TLB entries (FIFO eviction)

# Page table dimensions
PAGE_TABLES_L1 = 2   # number of L1 tables inside the page directory
PAGE_TABLES_L2 = 4   # number of L2 tables inside each L1 table


L1_BITS   = 1   # 2^1 = 2  → PAGE_TABLES_L1
L2_BITS   = 2   # 2^2 = 4  → PAGE_TABLES_L2
SLOT_BITS = 5   # 2^5 = 32 → slots per L2 table
