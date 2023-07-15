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
    def add_workspace(self, workspace_path: str) -> bool:
        """
        Adds a new workspace to the workspace service.

        Args:
            workspace_path (str): The root path of the workspace to be added.

        Returns:
            bool: True if the workspace was added successfully, False otherwise.
        """
        try:
            workspace_service.add_workspace(workspace_path)
            return True
        except Exception as e:
            print(f"Error while adding workspace: {e}")
            return False@strawberry.type

schema = strawberry.Schema(query=Query, mutation=Mutation)
