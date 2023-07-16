import os
import tempfile
import fnmatch

import pytest
from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal
from src.source_code_tree.file_explorer.traversal_ignore_strategy.git_ignore_strategy import GitIgnoreStrategy

def test_directory_traversal_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        dir_traversal = DirectoryTraversal([GitIgnoreStrategy(tmpdirname)])
        tree = dir_traversal.build_tree(tmpdirname)

        assert tree.name == os.path.basename(tmpdirname)
        assert tree.path == tmpdirname
        assert not tree.is_file
        assert tree.children == []


def test_directory_traversal_non_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        open(os.path.join(tmpdirname, 'file1.txt'), 'a').close()
        os.makedirs(os.path.join(tmpdirname, 'dir1'))

        dir_traversal = DirectoryTraversal([GitIgnoreStrategy(tmpdirname)])
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

        dir_traversal = DirectoryTraversal([GitIgnoreStrategy(tmpdirname)])
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
        dir_traversal = DirectoryTraversal([GitIgnoreStrategy(os.path.dirname(tmpfile.name))])
        tree = dir_traversal.build_tree(tmpfile.name)

        assert tree.name == os.path.basename(tmpfile.name)
        assert tree.path == tmpfile.name
        assert tree.is_file
        assert tree.children == []


def test_directory_traversal_non_existent_path():
    non_existent_path = '/non/existent/path'
    dir_traversal = DirectoryTraversal([GitIgnoreStrategy(non_existent_path)])

    with pytest.raises(FileNotFoundError):
        dir_traversal.build_tree(non_existent_path)


def test_directory_traversal_git_ignore_strategy():
    with tempfile.TemporaryDirectory() as tmpdirname:
        open(os.path.join(tmpdirname, 'file1.txt'), 'a').close()
        open(os.path.join(tmpdirname, 'file2.txt'), 'a').close()
        os.makedirs(os.path.join(tmpdirname, 'dir1'))
        os.makedirs(os.path.join(tmpdirname, 'dir2'))
        open(os.path.join(tmpdirname, 'dir2', 'file3.txt'), 'a').close()
        open(os.path.join(tmpdirname, 'dir2', 'file4.txt'), 'a').close()

        with open(os.path.join(tmpdirname, '.gitignore'), 'w') as gitignore_file:
            gitignore_file.write('file1.txt\n')
            gitignore_file.write('dir1/\n')
            gitignore_file.write('dir2/file3.txt\n')

        dir_traversal = DirectoryTraversal([GitIgnoreStrategy(tmpdirname)])
        tree = dir_traversal.build_tree(tmpdirname)

        assert tree.name == os.path.basename(tmpdirname)
        assert tree.path == tmpdirname
        assert not tree.is_file
        assert len(tree.children) == 3
        assert any(child.name == 'file2.txt' and child.is_file for child in tree.children)
        assert any(child.name == '.gitignore' and child.is_file for child in tree.children)
        assert any(child.name == 'dir2' and not child.is_file and len(child.children) == 1 for child in tree.children)
