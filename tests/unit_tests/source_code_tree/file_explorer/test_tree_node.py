# tests/unit_tests/source_code_tree/file_explorer/test_tree_node.py

import json
import pytest
from src.source_code_tree.file_explorer.tree_node import TreeNode


def test_tree_node_init():
    root_dir = TreeNode('root_dir', '/root_dir')

    assert root_dir.name == 'root_dir'
    assert root_dir.path == '/root_dir'
    assert root_dir.is_file == False
    assert root_dir.children == []


def test_tree_node_add_child():
    root_dir = TreeNode('root_dir', '/root_dir')
    sub_dir1 = TreeNode('sub_dir1', '/root_dir/sub_dir1')
    file1 = TreeNode('file1.txt', '/root_dir/sub_dir1/file1.txt', True)
    
    sub_dir1.add_child(file1)
    root_dir.add_child(sub_dir1)
    
    assert len(root_dir.children) == 1
    assert root_dir.children[0] == sub_dir1
    assert len(sub_dir1.children) == 1
    assert sub_dir1.children[0] == file1


def test_tree_node_to_dict():
    root_dir = TreeNode('root_dir', '/root_dir')
    sub_dir1 = TreeNode('sub_dir1', '/root_dir/sub_dir1')
    file1 = TreeNode('file1.txt', '/root_dir/sub_dir1/file1.txt', True)

    sub_dir1.add_child(file1)
    root_dir.add_child(sub_dir1)
    
    expected_dict = {
        'name': 'root_dir',
        'path': '/root_dir',
        'is_file': False,
        'children': [
            {
                'name': 'sub_dir1',
                'path': '/root_dir/sub_dir1',
                'is_file': False,
                'children': [
                    {
                        'name': 'file1.txt',
                        'path': '/root_dir/sub_dir1/file1.txt',
                        'is_file': True,
                        'children': []
                    }
                ]
            }
        ]
    }
    
    assert root_dir.to_dict() == expected_dict


def test_tree_node_to_json():
    root_dir = TreeNode('root_dir', '/root_dir')
    sub_dir1 = TreeNode('sub_dir1', '/root_dir/sub_dir1')
    file1 = TreeNode('file1.txt', '/root_dir/sub_dir1/file1.txt', True)

    sub_dir1.add_child(file1)
    root_dir.add_child(sub_dir1)

    expected_json = json.dumps(root_dir.to_dict(), indent=4)
    
