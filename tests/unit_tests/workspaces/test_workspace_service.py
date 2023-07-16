# tests/unit_tests/workspaces/test_workspace_service.py
"""
This module provides tests for the WorkspaceService.
"""

import os
import tempfile
from src.source_code_tree.file_explorer.directory_traversal import DirectoryTraversal
from src.workspaces.workspace_service import WorkspaceService
from src.source_code_tree.file_explorer.tree_node import TreeNode
from src.workspaces.workspace_setting import WorkspaceSetting

def test_should_add_workspace_successfully():
    """
    Test the add_workspace method should add workspace successfully.
    """
    # Arrange
    temp_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(temp_dir, 'test_directory'))  # Create a subdirectory in the temporary directory

    service = WorkspaceService()

    # Act
    tree = service.add_workspace(temp_dir)

    # Assert
    assert tree.name == os.path.basename(temp_dir)
    assert tree.path == temp_dir
    assert tree.is_file == False
    assert service.workspace_settings[temp_dir] is not None
    assert len(tree.children) == 1  # As we have created one subdirectory
    assert tree.children[0].name == 'test_directory'

def test_should_retrieve_workspace_setting():
    """
    Test the get_workspace_setting method should retrieve workspace setting correctly.
    """
    # Arrange
    temp_dir = tempfile.mkdtemp()
    service = WorkspaceService()
    service.add_workspace(temp_dir)

    # Act
    setting = service.get_workspace_setting(temp_dir)

    # Assert
    assert isinstance(setting, WorkspaceSetting)
