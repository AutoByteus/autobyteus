# src/semantic_code/schema.py
"""
This file contains the GraphQL schema for the project. 
It includes the `Query` and `Mutation` types, which define 
the available queries and mutations that the client can execute.
"""
import json
import strawberry
from strawberry.scalars import JSON
from src.config import config
from src.workspaces.workspace_service import WorkspaceService
from src.workspaces.workspace_setting import WorkspaceSetting
from src.endpoints.graphql.json.custom_json_encoder import CustomJSONEncoder
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.automated_coding_workflow.config import WORKFLOW_CONFIG


workflow = AutomatedCodingWorkflow()
workspace_service: WorkspaceService = WorkspaceService()

@strawberry.type
class Query:
    @strawberry.field
    def workflow_config(self) -> JSON:
        custom_encoder = CustomJSONEncoder()
        return custom_encoder.encode(WORKFLOW_CONFIG)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def start_workflow(self) -> bool:
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
            workspace_tree = workspace_service.add_workspace(workspace_root_path)
            return workspace_tree.to_json()
        except Exception as e:
            return json.dumps({"error": f"Error while adding workspace: {str(e)}"})

schema = strawberry.Schema(query=Query, mutation=Mutation)
