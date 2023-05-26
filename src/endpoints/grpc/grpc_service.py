"""
src/services/grpc_service.py: Provides a gRPC service implementation for the AutomatedCodingWorkflow.
"""


import src.proto.grpc_service_pb2 as automated_coding_workflow_pb2
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc
from src.automated_coding_workflow.config import WORKFLOW_CONFIG
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.workflow_types.types.workflow_template_config import StageTemplateConfig

class AutomatedCodingWorkflowService(automated_coding_workflow_pb2_grpc.AutomatedCodingWorkflowServiceServicer):
    """
    A gRPC service class that allows a client to control and interact with an automated coding workflow.

    The AutomatedCodingWorkflowService class extends the gRPC base class for service implementation.
    """

    def __init__(self):
        """
        Constructs a new instance of the AutomatedCodingWorkflowService class.
        """
        self.workflow = AutomatedCodingWorkflow()

    def StartWorkflow(self, request, context):
        """
        Starts the automated coding workflow and responds with a status message.

        Args:
            request: The request message from the gRPC client.
            context: The context of the gRPC call.

        Returns:
            A StartWorkflowResponse object indicating the result of the operation.
        """
        self.workflow.start_workflow()
        return automated_coding_workflow_pb2.StartWorkflowResponse(result="Workflow started successfully")

    def GetWorkflowConfig(self, request, context):
        """
        Provides the configuration of the automated coding workflow.

        Args:
            request: The request message from the gRPC client.
            context: The context of the gRPC call.

        Returns:
            A GetWorkflowConfigResponse object that represents the workflow configuration.
        """
        return _build_workflow_config_protobuf()

    def SetWorkspacePath(self, request, context):
        """
        Sets the workspace path for the workflow. If the operation is successful, it will return True. 
        If an error occurs, it will return False and the error message.

        Args:
            request: The request message from the gRPC client, should include 'workspace_path'.
            context: The context of the gRPC call.

        Returns:
            A SetWorkspacePathResponse object indicating the success status and potential error message.
        """
        try:
            self.workflow.config.workspace_path = request.workspace_path
            # You can add validation logic here
            return automated_coding_workflow_pb2.SetWorkspacePathResponse(success=True)
        except Exception as e:
            return automated_coding_workflow_pb2.SetWorkspacePathResponse(success=False, error_message=str(e))

def _build_workflow_config_protobuf():
    """
    A helper function to construct the workflow configuration protobuf message.

    Returns:
        A GetWorkflowConfigResponse object representing the workflow configuration.
    """
    workflow_config = automated_coding_workflow_pb2.GetWorkflowConfigResponse()

    for stage_name, stage_data in WORKFLOW_CONFIG['stages'].items():
        stage = _build_stage_protobuf(stage_name, stage_data)
        workflow_config.stages.add().CopyFrom(stage)

    return workflow_config

def _build_stage_protobuf(stage_name: str, stage_data: StageTemplateConfig):
    """
    A helper function to construct a Stage protobuf message.

    Args:
        stage_name (str): The name of the stage.
        stage_data (StageTemplateConfig): The configuration data for the stage.

    Returns:
        A Stage object that represents a stage in the workflow.
    """
    stage = automated_coding_workflow_pb2.Stage()
    stage.stage_name = stage_name

    stage.stage_class = stage_data["stage_class"].__name__
    if "stages" in stage_data:
        for substage_name, substage_data in stage_data["stages"].items():
            substage = _build_stage_protobuf(substage_name, substage_data)
            stage.stages.add().CopyFrom(substage)

    return stage

