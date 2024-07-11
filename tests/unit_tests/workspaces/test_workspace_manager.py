"""
This module provides tests for the WorkspaceManager.
"""

import os
import tempfile
from autobyteus.codeverse.core.file_explorer.directory_traversal import DirectoryTraversal
from autobyteus.workspaces.workspace_manager import WorkspaceManager
from autobyteus.codeverse.core.file_explorer.tree_node import TreeNode
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting

def test_should_add_workspace_successfully():
    """
    Test the add_workspace method of WorkspaceManager should add workspace successfully.
    """
    # Arrange
    temp_dir = tempfile.mkdtemp()
    os.mkdir(os.path.join(temp_dir, 'test_directory'))  # Create a subdirectory in the temporary directory
    manager = WorkspaceManager()

    # Act
    tree = manager.add_workspace(temp_dir)

    # Assert
    assert tree.name == os.path.basename(temp_dir)
    assert tree.path == temp_dir
    assert tree.is_file == False
    assert manager.get_workspace_setting(temp_dir) is not None
    assert len(tree.children) == 1  # As we have created one subdirectory
    assert tree.children[0].name == 'test_directory'

def test_should_retrieve_workspace_setting():
    """
    Test the get_workspace_setting method of WorkspaceManager should retrieve workspace setting correctly.
    """
    # Arrange
    temp_dir = tempfile.mkdtemp()
    manager = WorkspaceManager()
    manager.add_workspace(temp_dir)

    # Act
    setting = manager.get_workspace_setting(temp_dir)

    # Assert
    assert isinstance(setting, WorkspaceSetting)
