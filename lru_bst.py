"""
lru_bst.py
==========
AVL-balanced binary search tree for O(log n) LRU tracking.

Nodes are ordered by last-access timestamp.  The leftmost node (minimum
timestamp) is always the least-recently-used entry — remove_oldest()
finds and deletes it in O(log n).

Each access updates the node for its key: the old node is deleted and a
new one re-inserted with the current timestamp, keeping the BST ordering
invariant correct.

A companion dict (_ts_map) gives O(1) key → timestamp lookup so that
re-insertions and targeted removals do not require a tree search.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
#  Internal node
# ---------------------------------------------------------------------------

class _Node:
    __slots__ = ("key", "ts", "left", "right", "height")

    def __init__(self, key: tuple[str, int], ts: datetime) -> None:
        self.key:    tuple[str, int]  = key
        self.ts:     datetime         = ts
        self.left:   Optional[_Node]  = None
        self.right:  Optional[_Node]  = None
        self.height: int              = 1


# ---------------------------------------------------------------------------
#  AVL helpers
# ---------------------------------------------------------------------------

def _height(n: Optional[_Node]) -> int:
    return n.height if n else 0


def _update_height(n: _Node) -> None:
    n.height = 1 + max(_height(n.left), _height(n.right))


def _balance_factor(n: _Node) -> int:
    return _height(n.left) - _height(n.right)


def _rotate_right(y: _Node) -> _Node:
    x       = y.left
    y.left  = x.right
    x.right = y
    _update_height(y)
    _update_height(x)
    return x


def _rotate_left(x: _Node) -> _Node:
    y       = x.right
    x.right = y.left
    y.left  = x
    _update_height(x)
    _update_height(y)
    return y


def _rebalance(n: _Node) -> _Node:
    _update_height(n)
    bf = _balance_factor(n)

    if bf > 1:                        # left-heavy
        if _balance_factor(n.left) < 0:
            n.left = _rotate_left(n.left)    # Left-Right case
        return _rotate_right(n)

    if bf < -1:                       # right-heavy
        if _balance_factor(n.right) > 0:
            n.right = _rotate_right(n.right) # Right-Left case
        return _rotate_left(n)

    return n


# ---------------------------------------------------------------------------
#  BST insert / delete
# ---------------------------------------------------------------------------

def _insert(root: Optional[_Node], node: _Node) -> _Node:
    if root is None:
        return node
    if node.ts <= root.ts:
        root.left  = _insert(root.left,  node)
    else:
        root.right = _insert(root.right, node)
    return _rebalance(root)


def _min_node(n: _Node) -> _Node:
    while n.left:
        n = n.left
    return n


def _delete(
    root: Optional[_Node],
    key:  tuple[str, int],
    ts:   datetime,
) -> Optional[_Node]:
    """Delete the node whose (key, ts) matches exactly."""
    if root is None:
        return None

    if ts < root.ts:
        root.left  = _delete(root.left,  key, ts)
    elif ts > root.ts:
        root.right = _delete(root.right, key, ts)
    else:
        # Timestamp matches — confirm by key (handles duplicate timestamps)
        if root.key == key:
            if root.left is None:
                return root.right
            if root.right is None:
                return root.left
            # Two children: replace with in-order successor
            succ       = _min_node(root.right)
            root.key   = succ.key
            root.ts    = succ.ts
            root.right = _delete(root.right, succ.key, succ.ts)
        else:
            # Same timestamp, different key — search both subtrees
            root.left  = _delete(root.left,  key, ts)
            root.right = _delete(root.right, key, ts)

    return _rebalance(root)


# ---------------------------------------------------------------------------
#  Public class
# ---------------------------------------------------------------------------

class LRUBST:
    """
    AVL-balanced BST that tracks least-recently-used (key, timestamp) pairs.

    Keys are (file_id, vpn) tuples.  The oldest entry (smallest timestamp)
    is always retrievable in O(log n) via remove_oldest().
    """

    def __init__(self) -> None:
        self._root:   Optional[_Node]                        = None
        self._ts_map: dict[tuple[str, int], datetime]        = {}

    # ------------------------------------------------------------------

    def touch(self, key: tuple[str, int], ts: datetime) -> None:
        """
        Record an access for *key* at time *ts*.

        If the key is already tracked, the old node is removed before
        re-insertion so the BST ordering stays correct.
        """
        if key in self._ts_map:
            self._root = _delete(self._root, key, self._ts_map[key])

        node       = _Node(key, ts)
        self._root = _insert(self._root, node)
        self._ts_map[key] = ts

    def remove_oldest(self) -> Optional[tuple[str, int]]:
        """
        Remove and return the key with the smallest (oldest) timestamp.

        Returns None if the tracker is empty.
        """
        if self._root is None:
            return None

        oldest = _min_node(self._root)
        key, ts = oldest.key, oldest.ts
        self._root = _delete(self._root, key, ts)
        del self._ts_map[key]
        return key

    def remove(self, key: tuple[str, int]) -> None:
        """Explicitly evict *key* (called when a page is unmapped externally)."""
        if key not in self._ts_map:
            return
        ts = self._ts_map.pop(key)
        self._root = _delete(self._root, key, ts)

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._ts_map)

    def __contains__(self, key: object) -> bool:
        return key in self._ts_map
