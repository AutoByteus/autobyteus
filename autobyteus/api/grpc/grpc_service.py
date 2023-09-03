"""
autobyteus/services/grpc_service.py: Provides a gRPC service implementation for the AutomatedCodingWorkflow.
"""


import autobyteus.proto.grpc_service_pb2 as automated_coding_workflow_pb2
import autobyteus.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc
from autobyteus.workflow.automated_coding_workflow import AutomatedCodingWorkflow
from autobyteus.workflow.config import WORKFLOW_CONFIG
from autobyteus.workflow.types.workflow_template_config import StepsTemplateConfig

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

    for step_name, step_data in WORKFLOW_CONFIG['steps'].items():
        step = _build_step_protobuf(step_name, step_data)
        workflow_config.steps.add().CopyFrom(step)

    return workflow_config

def _build_step_protobuf(step_name: str, step_data: StepsTemplateConfig):
    """
    A helper function to construct a Step protobuf message.

    Args:
        step_name (str): The name of the step.
        step_data (StepsTemplateConfig): The configuration data for the step.

    Returns:
        A Step object that represents a step in the workflow.
    """
    step = automated_coding_workflow_pb2.Step()
    step.step_name = step_name

    step.step_class = step_data["step_class"].__name__
    if "steps" in step_data:
        for substep_name, substep_data in step_data["steps"].items():
            substep = _build_step_protobuf(substep_name, substep_data)
            step.steps.add().CopyFrom(substep)

    return step
