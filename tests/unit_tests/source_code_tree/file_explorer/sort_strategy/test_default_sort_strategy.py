# tests/unit_tests/source_code_tree/file_explorer/sort_strategy/test_default_sort_strategy.py

import os
import pytest
import tempfile
from src.source_code_tree.file_explorer.sort_strategy.default_sort_strategy import DefaultSortStrategy


@pytest.fixture
def sort_strategy()-> DefaultSortStrategy:
    return DefaultSortStrategy()


@pytest.fixture
def setup_files_and_folders():
    # Creating nested temporary directories and files for testing.
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, '.dot_dir', 'nested_dir'))
        os.makedirs(os.path.join(tmp_dir, 'normal_dir', 'nested_dir'))
        os.makedirs(os.path.join(tmp_dir, '.dot_dir', '.nested_dot_dir'))
        os.makedirs(os.path.join(tmp_dir, 'normal_dir', '.nested_dot_dir'))
        
        with open(os.path.join(tmp_dir, '.dot_file'), 'w') as f:
            f.write('dot file')
        with open(os.path.join(tmp_dir, 'normal_file'), 'w') as f:
            f.write('normal file')
        with open(os.path.join(tmp_dir, '.dot_dir', 'nested_file'), 'w') as f:
            f.write('nested file')
        with open(os.path.join(tmp_dir, 'normal_dir', 'nested_file'), 'w') as f:
            f.write('nested file')
        with open(os.path.join(tmp_dir, '.dot_dir', '.nested_dot_file'), 'w') as f:
            f.write('nested dot file')
        with open(os.path.join(tmp_dir, 'normal_dir', '.nested_dot_file'), 'w') as f:
            f.write('nested dot file')

        yield tmp_dir



def test_sorts_folders_and_files_correctly(sort_strategy: DefaultSortStrategy, setup_files_and_folders):
    # Arrange
    paths = [os.path.join(setup_files_and_folders, path_name) 
             for path_name in os.listdir(setup_files_and_folders)]

    # Act
    sorted_paths = sort_strategy.sort(paths)

    # Assert
    assert sorted_paths == [
        os.path.join(setup_files_and_folders, '.dot_dir'),
        os.path.join(setup_files_and_folders, 'normal_dir'),
        os.path.join(setup_files_and_folders, '.dot_file'),
        os.path.join(setup_files_and_folders, 'normal_file'),
    ]

    # Testing the nested directories in '.dot_dir'
    dot_dir_paths = [os.path.join(setup_files_and_folders, '.dot_dir', path_name)
                     for path_name in os.listdir(os.path.join(setup_files_and_folders, '.dot_dir'))]
    sorted_dot_dir_paths = sort_strategy.sort(dot_dir_paths)
    assert sorted_dot_dir_paths == [
        os.path.join(setup_files_and_folders, '.dot_dir', '.nested_dot_dir'),
        os.path.join(setup_files_and_folders, '.dot_dir', 'nested_dir'),
        os.path.join(setup_files_and_folders, '.dot_dir', '.nested_dot_file'),
        os.path.join(setup_files_and_folders, '.dot_dir', 'nested_file'),
    ]

    # Testing the nested directories in 'normal_dir'
    normal_dir_paths = [os.path.join(setup_files_and_folders, 'normal_dir', path_name)
                        for path_name in os.listdir(os.path.join(setup_files_and_folders, 'normal_dir'))]
    sorted_normal_dir_paths = sort_strategy.sort(normal_dir_paths)
    assert sorted_normal_dir_paths == [
        os.path.join(setup_files_and_folders, 'normal_dir', '.nested_dot_dir'),
        os.path.join(setup_files_and_folders, 'normal_dir', 'nested_dir'),
        os.path.join(setup_files_and_folders, 'normal_dir', '.nested_dot_file'),
        os.path.join(setup_files_and_folders, 'normal_dir', 'nested_file'),
    ]
