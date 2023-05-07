"""
tree_formatter.py: A Python module that provides the TreeFormatter class.

The TreeFormatter class is responsible for formatting the tree structure with appropriate
indentation and symbols for a user-friendly display.

Features:
- Format a tree structure for user-friendly display.

Usage:
- from tree_formatter import TreeFormatter
- tf = TreeFormatter()
- formatted_tree = tf.format_tree(tree_structure)
"""

class TreeFormatter:
    def format_tree(self, tree_structure):
        formatted_tree = []

        for item, level, is_folder in tree_structure:
            indent = " " * (level * 4)
            symbol = "+" if is_folder else "-"
            formatted_tree.append(f"{indent}{symbol} {item}")

        return "\n".join(formatted_tree)
