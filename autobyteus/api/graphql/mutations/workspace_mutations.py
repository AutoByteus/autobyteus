"""
Module: workspace_mutations

This module provides GraphQL mutations related to workspace operations.
"""

import json
import logging
import strawberry
from strawberry.scalars import JSON
from src.workspaces.workspace_manager import WorkspaceManager
from src.workspaces.errors.workspace_already_exists_error import WorkspaceAlreadyExistsError
from src.source_code_tree.file_explorer.tree_node import TreeNode

# Singleton instances
workspace_manager = WorkspaceManager()

# Logger setup
logger = logging.getLogger(__name__)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def start_workflow(self, workspace_root_path: str) -> bool:
        """
        Starts the workflow associated with the provided workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            bool: True if the workflow was started successfully, otherwise False.
        """
        workflow = workspace_manager.workflows.get(workspace_root_path)
        if not workflow:
            return False

        workflow.start_workflow()
        return True

    @strawberry.mutation
    def add_workspace(self, workspace_root_path: str) -> JSON:
        """
        Adds a new workspace to the workspace service and
        returns a JSON representation of the workspace directory tree.

        Args:
            workspace_root_path (str): The root path of the workspace to be added.

        Returns:
            JSON: The JSON representation of the workspace directory tree if the workspace
            was added successfully, otherwise a JSON with an error message.
        """
        try:
            workspace_tree: TreeNode = workspace_manager.add_workspace(workspace_root_path)
            return workspace_tree.to_json()
        except WorkspaceAlreadyExistsError as e:
            error_message = str(e)
            logger.error(error_message)
            return json.dumps({"error": error_message})
        except Exception as e:
            error_message = f"Error while adding workspace: {str(e)}"
            logger.error(error_message)
            return json.dumps({"error": error_message})