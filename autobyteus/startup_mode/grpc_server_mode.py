from concurrent import futures
import grpc
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc


def grpc_server_mode():
    print("Running in gRPC server mode")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    automated_coding_workflow_pb2_grpc.add_AutomatedCodingWorkflowServiceServicer_to_server(AutomatedCodingWorkflowService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
