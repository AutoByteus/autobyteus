# tests/unit_tests/source_code_tree/file_explorer/sort_strategy/test_default_sort_strategy.py

import os
import pytest
import tempfile
from autobyteus.codeverse.core.file_explorer.sort_strategy.default_sort_strategy import DefaultSortStrategy


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
    ], "Sorting at root level failed."

    # Testing the nested directories in '.dot_dir'
    dot_dir_paths = [os.path.join(setup_files_and_folders, '.dot_dir', path_name)
                     for path_name in os.listdir(os.path.join(setup_files_and_folders, '.dot_dir'))]
    sorted_dot_dir_paths = sort_strategy.sort(dot_dir_paths)
    assert sorted_dot_dir_paths == [
        os.path.join(setup_files_and_folders, '.dot_dir', '.nested_dot_dir'),
        os.path.join(setup_files_and_folders, '.dot_dir', 'nested_dir'),
        os.path.join(setup_files_and_folders, '.dot_dir', '.nested_dot_file'),
        os.path.join(setup_files_and_folders, '.dot_dir', 'nested_file'),
    ], "Sorting in '.dot_dir' failed."

    # Testing the nested directories in 'normal_dir'
    normal_dir_paths = [os.path.join(setup_files_and_folders, 'normal_dir', path_name)
                        for path_name in os.listdir(os.path.join(setup_files_and_folders, 'normal_dir'))]
    sorted_normal_dir_paths = sort_strategy.sort(normal_dir_paths)
    assert sorted_normal_dir_paths == [
        os.path.join(setup_files_and_folders, 'normal_dir', '.nested_dot_dir'),
        os.path.join(setup_files_and_folders, 'normal_dir', 'nested_dir'),
        os.path.join(setup_files_and_folders, 'normal_dir', '.nested_dot_file'),
        os.path.join(setup_files_and_folders, 'normal_dir', 'nested_file'),
    ], "Sorting in 'normal_dir' failed."


# Create test files and directories
@pytest.fixture
def create_test_directory_structure(tmp_path):
    directories = ['src', '.vscode', 'public']
    files = ['README.md', 'codegen.yml', 'graphql.schema.json', 'index.html', 'package-lock.json', 'package.json', 'tsconfig.json', 'tsconfig.node.json', 'vite.config.ts', 'yarn.lock', '.gitignore']

    for directory in directories:
        (tmp_path / directory).mkdir()

    for file in files:
        (tmp_path / file).touch()

    return [str(tmp_path / name) for name in directories + files]


def test_default_sort_strategy(create_test_directory_structure, tmp_path):
    # Arrange
    sort_strategy = DefaultSortStrategy()
    unsorted_paths = create_test_directory_structure

    # Act
    sorted_paths = sort_strategy.sort(unsorted_paths)

    # Assert
    expected_order = ['.vscode', 'public', 'src', '.gitignore', 'README.md', 'codegen.yml', 'graphql.schema.json', 'index.html', 'package-lock.json', 'package.json', 'tsconfig.json', 'tsconfig.node.json', 'vite.config.ts', 'yarn.lock']
    expected_order = [str(tmp_path / path) for path in expected_order]  # Convert to string to compare with sorted_paths

    assert sorted_paths == expected_order, f"Expected order is {expected_order}, but got {sorted_paths}"
