"""
Module: workspace_indexer

This module provides the `WorkspaceIndexer` class, which is responsible for indexing 
all source code entities within a workspace. This is achieved by parsing each source 
code file and indexing its parsed entities. The indexer operates within the context 
of a specific workspace, as provided by the `WorkspaceSetting`.
"""

import os
from autobyteus.codeverse.index.index_service import IndexService
from autobyteus.codeverse.core.code_parser.code_file_parser import CodeFileParser
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting
from autobyteus.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool


class WorkspaceIndexer(BaseWorkspaceTool):
    """
    Handles parsing and indexing of source code entities within a workspace.
    """

    def __init__(self, workspace_setting: WorkspaceSetting):
        """
        Initialize a WorkspaceIndexer.

        Args:
            workspace_setting (WorkspaceSetting): The settings of the workspace.
        """
        self.workspace_setting = workspace_setting
        self.index_service = IndexService()
        self.parser = CodeFileParser()

    def index_workspace(self) -> None:
        """
        Index all source code entities within the workspace.
        """
        for root, dirs, files in os.walk(self.workspace_setting.root_path):
            for file in files:
                # Optionally, add a filter here based on file extensions
                # For example: if file.endswith('.py'):
                file_path = os.path.join(root, file)
                self._parse_and_index_file(file_path)

    def _parse_and_index_file(self, file_path: str) -> None:
        """
        Parse and index entities from a given source code file within the workspace.

        Args:
            file_path (str): Absolute path to the source code file.
        """
        module_entity = self.parser.parse_source_code(file_path)
        try:
            self.index_service.index(module_entity)
        except Exception as e:
            # Logging can be added here to provide insights into any indexing failures
            print(f"Failed to index entities from {file_path}. Error: {str(e)}")

