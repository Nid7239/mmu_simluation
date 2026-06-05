"""
constants.py
============
Simulation-wide configuration for the MMU.

Page table hierarchy
--------------------
Level 0 : PageDirectory          — 1 instance, the single root
Level 1 : L1PageTable            — PAGE_TABLES_L1 (2) instances inside the directory
Level 2 : PageTable              — PAGE_TABLES_L2 (4) instances inside each L1 table

VPN bit layout  (bits counted from the MSB of the used portion)
---------------------------------------------------------------
  Bit  7      → l1_idx   selects which L1 table  (0 or 1)
  Bits 6–5    → l2_idx   selects which L2 table  (0–3)
  Bits 4–0    → slot     entry within the L2 table (0–31)
"""

# Physical memory
PAGE_SIZE  = 64    # bytes per page / frame
NUM_FRAMES =4   # total physical frames in simulated RAM

# TLB
TLB_SIZE = 8       # maximum TLB entries (FIFO eviction)

# Page table dimensions
PAGE_TABLES_L1 = 2   # number of L1 tables inside the page directory
PAGE_TABLES_L2 = 4   # number of L2 tables inside each L1 table

# VPN bit-field widths  (must satisfy 2^width == matching table count)
L1_BITS   = 1   # 2^1 = 2  → PAGE_TABLES_L1
L2_BITS   = 2   # 2^2 = 4  → PAGE_TABLES_L2
SLOT_BITS = 5   # 2^5 = 32 → slots per L2 table
