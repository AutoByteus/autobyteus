# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: grpc_service.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12grpc_service.proto\x12\x17\x61utomatedcodingworkflow\"\x16\n\x14StartWorkflowRequest\"\'\n\x15StartWorkflowResponse\x12\x0e\n\x06result\x18\x01 \x01(\t\"\x1a\n\x18GetWorkflowConfigRequest\"I\n\x19GetWorkflowConfigResponse\x12,\n\x05steps\x18\x01 \x03(\x0b\x32\x1d.automatedcodingworkflow.Step\"[\n\x04Step\x12\x11\n\tstep_name\x18\x01 \x01(\t\x12\x12\n\nstep_class\x18\x02 \x01(\t\x12,\n\x05steps\x18\x03 \x03(\x0b\x32\x1d.automatedcodingworkflow.Step\"1\n\x17SetWorkspacePathRequest\x12\x16\n\x0eworkspace_path\x18\x01 \x01(\t\"B\n\x18SetWorkspacePathResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t2\x85\x03\n\x1e\x41utomatedCodingWorkflowService\x12n\n\rStartWorkflow\x12-.automatedcodingworkflow.StartWorkflowRequest\x1a..automatedcodingworkflow.StartWorkflowResponse\x12z\n\x11GetWorkflowConfig\x12\x31.automatedcodingworkflow.GetWorkflowConfigRequest\x1a\x32.automatedcodingworkflow.GetWorkflowConfigResponse\x12w\n\x10SetWorkspacePath\x12\x30.automatedcodingworkflow.SetWorkspacePathRequest\x1a\x31.automatedcodingworkflow.SetWorkspacePathResponseb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'grpc_service_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _STARTWORKFLOWREQUEST._serialized_start=47
  _STARTWORKFLOWREQUEST._serialized_end=69
  _STARTWORKFLOWRESPONSE._serialized_start=71
  _STARTWORKFLOWRESPONSE._serialized_end=110
  _GETWORKFLOWCONFIGREQUEST._serialized_start=112
  _GETWORKFLOWCONFIGREQUEST._serialized_end=138
  _GETWORKFLOWCONFIGRESPONSE._serialized_start=140
  _GETWORKFLOWCONFIGRESPONSE._serialized_end=213
  _STEP._serialized_start=215
  _STEP._serialized_end=306
  _SETWORKSPACEPATHREQUEST._serialized_start=308
  _SETWORKSPACEPATHREQUEST._serialized_end=357
  _SETWORKSPACEPATHRESPONSE._serialized_start=359
  _SETWORKSPACEPATHRESPONSE._serialized_end=425
  _AUTOMATEDCODINGWORKFLOWSERVICE._serialized_start=428
  _AUTOMATEDCODINGWORKFLOWSERVICE._serialized_end=817
# @@protoc_insertion_point(module_scope)
