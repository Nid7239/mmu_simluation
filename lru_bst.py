from datetime import datetime
from typing import Optional, Tuple, Dict

class BSTNode:
    def __init__(self, key: Tuple[str, int], timestamp: datetime):
        self.key = key
        self.timestamp = timestamp
        self.left = None
        self.right = None
        self.parent = None
        self.height = 1

class LRUBST:
    def __init__(self):
        self.root = None
        self.node_map: Dict[Tuple[str, int], BSTNode] = {}

    # Height and Balance
    def _height(self, node):
        return node.height if node else 0

    def _update_height(self, node):
        if node:
            node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right)

    def _right_rotate(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        if t2: t2.parent = y
        x.parent = y.parent
        y.parent = x
        self._update_height(y)
        self._update_height(x)
        return x

    def _left_rotate(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        if t2: t2.parent = x
        y.parent = x.parent
        x.parent = y
        self._update_height(x)
        self._update_height(y)
        return y

    def _balance(self, node):
        if not node:
            return node
        self._update_height(node)
        bf = self._balance_factor(node)

        if bf > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._left_rotate(node.left)
            return self._right_rotate(node)
        if bf < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._right_rotate(node.right)
            return self._left_rotate(node)
        return node

    def insert(self, key: Tuple[str, int], timestamp: datetime):
        if key in self.node_map:
            self._delete_node(self.node_map[key])
        node = BSTNode(key, timestamp)
        self.node_map[key] = node
        self.root = self._insert_bst(self.root, node)
        self.root = self._balance(self.root)

    def _insert_bst(self, root, node):
        if not root:
            return node
        if node.timestamp < root.timestamp:
            root.left = self._insert_bst(root.left, node)
            if root.left: root.left.parent = root
        else:
            root.right = self._insert_bst(root.right, node)
            if root.right: root.right.parent = root
        return self._balance(root)

    def remove_oldest(self):
        if not self.root:
            return None
        key = self._get_oldest_key()
        self._delete_node(self.node_map[key])
        del self.node_map[key]
        if self.root:
            self.root = self._balance(self.root)
        return key

    def _get_oldest_key(self):
        curr = self.root
        while curr and curr.left:
            curr = curr.left
        return curr.key

    def _delete_node(self, node):
        if node.parent is None:
            self.root = None
        elif node == node.parent.left:
            node.parent.left = None
        else:
            node.parent.right = None
        if self.root:
            self.root = self._balance(self.root)