from datetime import datetime
from typing import Optional, Tuple, Dict

class BSTNode:
    def __init__(self, key: Tuple[str, int], timestamp: datetime):
        #Initializes the BST to index pages by their 'last accessed' time.
        self.key = key
        self.timestamp = timestamp
        self.left = None
        self.right = None
        self.parent = None

class LRUBST:
    def __init__(self):
        self.root = None
        self.node_map: Dict[Tuple[str, int], BSTNode] = {}

    def insert(self, key: Tuple[str, int], timestamp: datetime):
        if key in self.node_map:
            self._delete_node(self.node_map[key])
        node = BSTNode(key, timestamp)
        self.node_map[key] = node
        self._insert_bst(node)

    def remove_oldest(self) -> Optional[Tuple[str, int]]:
        if not self.root:
            return None
        
        oldest_node = self._get_minimum_node(self.root)
        key = oldest_node.key
        self._delete_node(oldest_node)
        return key

    def _get_minimum_node(self, node: BSTNode) -> BSTNode:
        curr = node
        while curr.left:
            curr = curr.left
        return curr

    def _insert_bst(self, node: BSTNode):
        if not self.root:
            self.root = node
            return
        curr = self.root
        while True:
            if node.timestamp < curr.timestamp:
                # New node is OLDER, so it MUST go left
                if not curr.left:
                    curr.left = node
                    node.parent = curr
                    break
                curr = curr.left
            else:
                # New node is NEWER, so it MUST go right
                if not curr.right:
                    curr.right = node
                    node.parent = curr
                    break
                curr = curr.right

    def _delete_node(self, node: BSTNode):
        # Clean up mapping before deletion
        if node.key in self.node_map:
            del self.node_map[node.key]

        if not node.left and not node.right:
            self._replace_node(node, None)
        elif not node.left:
            self._replace_node(node, node.right)
        elif not node.right:
            self._replace_node(node, node.left)
        else:
            # Node with two children: replace with successor
            successor = self._get_minimum_node(node.right)
            node.timestamp = successor.timestamp
            node.key = successor.key
            # Re-map the new key to this physical node reference
            self.node_map[node.key] = node
            self._delete_node(successor)

    def _replace_node(self, node: BSTNode, replacement: Optional[BSTNode]):
        if node.parent is None:
            self.root = replacement
        elif node == node.parent.left:
            node.parent.left = replacement
        else:
            node.parent.right = replacement
            
        if replacement:
            replacement.parent = node.parent