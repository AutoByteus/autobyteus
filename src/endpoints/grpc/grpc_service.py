# src/services/grpc_service.py
"""
grpc_service.py: Provides a gRPC service implementation for the AutomatedCodingWorkflow.
"""

import src.proto.grpc_service_pb2 as automated_coding_workflow_pb2
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc
from src.automated_coding_workflow.config import WORKFLOW_CONFIG
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.workflow_types.types.workflow_template_config import StageTemplateConfig

class AutomatedCodingWorkflowService(automated_coding_workflow_pb2_grpc.AutomatedCodingWorkflowServiceServicer):
    def __init__(self):
        self.workflow = AutomatedCodingWorkflow()

    def StartWorkflow(self, request, context):
        self.workflow.start_workflow()
        return automated_coding_workflow_pb2.StartWorkflowResponse(result="Workflow started successfully")

    def GetWorkflowConfig(self, request, context):
        return _build_workflow_config_protobuf()

    def SetWorkspacePath(self, request, context):
            try:
                self.workflow.config.workspace_path = request.workspace_path
                # You can add validation logic here
                return automated_coding_workflow_pb2.SetWorkspacePathResponse(success=True)
            except Exception as e:
                return automated_coding_workflow_pb2.SetWorkspacePathResponse(success=False, error_message=str(e))

def _build_workflow_config_protobuf():
    workflow_config = automated_coding_workflow_pb2.GetWorkflowConfigResponse()

    for stage_name, stage_data in WORKFLOW_CONFIG['stages']:
        stage = _build_stage_protobuf(stage_name, stage_data)
        workflow_config.stages.add().CopyFrom(stage)

    return workflow_config

def _build_stage_protobuf(stage_name: str, stage_data: StageTemplateConfig):
    stage = automated_coding_workflow_pb2.Stage()
    stage.stage_name = stage_name

    stage.class_name = stage_data["stage_class"]
    if "stages" in stage_data:
        for substage_name, substage_data in stage_data["stages"].items():
            substage = _build_stage_protobuf(substage_name, substage_data)
            stage.stages.add().CopyFrom(substage)

    return stage

