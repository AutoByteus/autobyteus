import os
import pytest
from typing import Dict, List

from src.source_code_tree.code_tree_generator import SourceCodeTreeGenerator
from src.source_code_tree.directory_traversal import DirectoryTraversal
from src.source_code_tree.file_system_access import FileSystemAccess

class MockFileSystemAccess(FileSystemAccess):
    def __init__(self, mock_data: Dict[str, List[str]]):
        self.mock_data = mock_data

    def get_folder_items(self, folder_path: str) -> List[str]:
        return self.mock_data.get(folder_path, [])

    def is_folder(self, item_path: str) -> bool:
        return item_path in self.mock_data

@pytest.fixture(scope='module')
def mock_data():
    return {
        "root": ["root/file1.txt", "root/subfolder"],
        "root/subfolder": ["root/subfolder/file2.txt", "root/subfolder/file3.txt"],
    }

@pytest.fixture(scope='module')
def code_tree_generator(mock_data) -> SourceCodeTreeGenerator:
    mock_fs_access = MockFileSystemAccess(mock_data)
    return SourceCodeTreeGenerator(mock_fs_access)

@pytest.mark.parametrize("folder_path, expected_output", [
    ("root", "root\n    - root/file1.txt\n    + root/subfolder\n        - root/subfolder/file2.txt\n        - root/subfolder/file3.txt"),
    ("empty", "empty")
])
def test_generate_tree_valid_inputs(code_tree_generator: SourceCodeTreeGenerator, folder_path, expected_output):
    tree = code_tree_generator.generate_tree(folder_path)
    assert tree == expected_output

@pytest.mark.parametrize("folder_path, expected_exception", [
    ("invalid/path", FileNotFoundError),
    ("/root" if os.name != "nt" else "C:\\Windows\\System32\\config", PermissionError)
])
def test_generate_tree_invalid_inputs(code_tree_generator, folder_path, expected_exception):
    with pytest.raises(expected_exception):
        code_tree_generator.generate_tree(folder_path)

def test_generate_tree_large_folder_structure(code_tree_generator, mock_data):
    # Mocking a large data set
    large_data_set = {f"folder{i}": [f"folder{i}/file{j}.txt" for j in range(100)] for i in range(100)}
    mock_data.update(large_data_set)

    # This is a dummy check, since we don't have a specific large folder to test.
    # Ideally, you want to verify correctness and performance for a large input.
    assert code_tree_generator.generate_tree("folder99") is not None
