from asyncio import futures
import grpc
from src.services.grpc_service import AutomatedCodingWorkflowService
import src.proto.grpc_service_pb2_grpc as automated_coding_workflow_pb2_grpc


def grpc_server_mode(config, host, port):
    """
    Run the application in gRPC server mode.
    
    :param config: Config object containing the loaded configuration.
    :param host: Server hostname.
    :param port: Server port.
    """
    print("Running in gRPC server mode")
    serve(host, port)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    automated_coding_workflow_pb2_grpc.add_AutomatedCodingWorkflowServiceServicer_to_server(AutomatedCodingWorkflowService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
    