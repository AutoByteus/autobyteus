# src/services/grpc_service.py
"""
grpc_service.py: Provides a gRPC service implementation for the AutomatedCodingWorkflow.
"""

import src.proto.grpc_service_pb2 as automated_coding_workflow_pb2
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc

from src.workflow.automated_coding_workflow import AutomatedCodingWorkflow

class AutomatedCodingWorkflowService(automated_coding_workflow_pb2_grpc.AutomatedCodingWorkflowServiceServicer):
    def __init__(self):
        self.workflow = AutomatedCodingWorkflow()

    def StartWorkflow(self, request, context):
        self.workflow.start_workflow()
        return automated_coding_workflow_pb2.StartWorkflowResponse(result="Workflow started successfully")

    def GetWorkflowConfig(self, request, context):
        return _build_workflow_config_protobuf()


def _build_stage_protobuf(stage_name, stage_data):
    stage = automated_coding_workflow_pb2.Stage()
    stage.name = stage_name
    stage.class_name = stage_data["class"]

    if "stages" in stage_data:
        for substage_name, substage_data in stage_data["stages"].items():
            substage = _build_stage_protobuf(substage_name, substage_data)
            stage.stages.add().CopyFrom(substage)

    return stage

def _build_workflow_config_protobuf(config):
    workflow_config = automated_coding_workflow_pb2.GetWorkflowConfigResponse()

    for stage_name, stage_data in config.items():
        stage = _build_stage_protobuf(stage_name, stage_data)
        workflow_config.stages.add().CopyFrom(stage)

    return workflow_config
