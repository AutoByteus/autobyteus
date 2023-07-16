import os
import tempfile

import pytest
from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal

import os
import tempfile
from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal

def test_directory_traversal_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        dir_traversal = DirectoryTraversal()
        tree = dir_traversal.build_tree(tmpdirname)
        
        assert tree.name == os.path.basename(tmpdirname)
        assert tree.path == tmpdirname
        assert not tree.is_file
        assert tree.children == []

def test_directory_traversal_non_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        open(os.path.join(tmpdirname, 'file1.txt'), 'a').close()
        os.makedirs(os.path.join(tmpdirname, 'dir1'))

        dir_traversal = DirectoryTraversal()
        tree = dir_traversal.build_tree(tmpdirname)

        assert tree.name == os.path.basename(tmpdirname)
        assert tree.path == tmpdirname
        assert not tree.is_file
        assert len(tree.children) == 2
        assert any(child.name == 'file1.txt' and child.is_file for child in tree.children)
        assert any(child.name == 'dir1' and not child.is_file for child in tree.children)

def test_directory_traversal_nested_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.makedirs(os.path.join(tmpdirname, 'dir1', 'dir2'))
        open(os.path.join(tmpdirname, 'dir1', 'file2.txt'), 'a').close()

        dir_traversal = DirectoryTraversal()
        tree = dir_traversal.build_tree(tmpdirname)

        assert tree.name == os.path.basename(tmpdirname)
        assert tree.path == tmpdirname
        assert not tree.is_file
        assert len(tree.children) == 1
        dir1 = tree.children[0]
        assert dir1.name == 'dir1'
        assert not dir1.is_file
        assert len(dir1.children) == 2
        assert any(child.name == 'dir2' and not child.is_file for child in dir1.children)
        assert any(child.name == 'file2.txt' and child.is_file for child in dir1.children)

def test_directory_traversal_file():
    with tempfile.NamedTemporaryFile() as tmpfile:
        dir_traversal = DirectoryTraversal()
        tree = dir_traversal.build_tree(tmpfile.name)

        assert tree.name == os.path.basename(tmpfile.name)
        assert tree.path == tmpfile.name
        assert tree.is_file
        assert tree.children == []

def test_directory_traversal_non_existent_path():
    dir_traversal = DirectoryTraversal()
    non_existent_path = '/non/existent/path'
    
    with pytest.raises(FileNotFoundError):
        dir_traversal.build_tree(non_existent_path)
