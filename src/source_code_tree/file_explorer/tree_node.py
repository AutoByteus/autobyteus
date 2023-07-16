import json


class TreeNode:
    """
    A class used to represent a file or directory in a directory structure.

    Attributes
    ----------
    name : str
        The name of the file or directory.
    path : str
        The full path of the file or directory.
    is_file : bool
        True if this node represents a file, False if it represents a directory.
    children : list[TreeNode]
        The children of this node. Each child is a TreeNode representing a file or subdirectory.

    Methods
    -------
    add_child(node: TreeNode)
        Adds a child to this node.
    """

    def __init__(self, name: str, path: str, is_file: bool = False):
        self.name = name
        self.path = path
        self.is_file = is_file
        self.children = []

    def add_child(self, node):
        """Adds a child to this node."""
        self.children.append(node)


    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the TreeNode.

        Returns:
            dict: The dictionary representation of the TreeNode.
        """
        return {
            "name": self.name,
            "path": self.path,
            "is_file": self.is_file,
            "children": [child.to_dict() for child in self.children],
        }

    def to_json(self) -> str:
        """
        Returns a JSON representation of the TreeNode.

        Returns:
            str: The JSON representation of the TreeNode.
        """
        return json.dumps(self.to_dict())