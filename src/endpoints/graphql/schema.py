# src/semantic_code/schema.py
"""
This file contains the GraphQL schema for the project.
It defines the available queries and mutations that the client can execute
related to the workflow and workspace management.
"""
import json
import logging
import strawberry
from strawberry.scalars import JSON
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.source_code_tree.file_explorer.tree_node import TreeNode
from src.workspaces.workspace_service import WorkspaceService
from src.endpoints.graphql.json.custom_json_encoder import CustomJSONEncoder
from src.automated_coding_workflow.config import WORKFLOW_CONFIG


# Singleton instance of WorkspaceService
workspace_service = WorkspaceService()

logger = logging.getLogger(__name__)

@strawberry.type
class Query:
    @strawberry.field
    def workflow_config(self, workspace_root_path: str) -> JSON:
        """
        Fetches the configuration for the workflow associated with the provided workspace.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            JSON: The configuration of the workflow.
        """
        workflow: AutomatedCodingWorkflow = workspace_service.workflows.get(workspace_root_path)
        if not workflow:
            return json.dumps({"error": "Workspace not found or workflow not initialized"})

        return workflow.to_json()

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
        workflow = workspace_service.workflows.get(workspace_root_path)
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
            workspace_tree: TreeNode = workspace_service.add_workspace(workspace_root_path)
            return workspace_tree.to_json()
        except Exception as e:
            error_message = f"Error while adding workspace: {str(e)}"
            logger.error(error_message)
            return json.dumps({"error": error_message})


schema = strawberry.Schema(query=Query, mutation=Mutation)
