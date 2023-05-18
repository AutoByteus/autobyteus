"""
app.py: The main entry point for a Python application with three modes of operation: command line, gRPC server mode, and GraphQL server mode.

The script allows users to:
- Interact with a chat system through PuppeteerLLMIntegration in command line mode.
- Run a gRPC server for AutomatedCodingWorkflowService in gRPC server mode.
- Run a FastAPI server with GraphQL endpoints using the Strawberry GraphQL library in GraphQL server mode.

The mode, configuration file, server hostname, and port are specified through command line arguments. The script parses these arguments and executes the appropriate mode function with the necessary parameters.

Usage:
- For command line mode: python app.py --mode commandline
- For gRPC server mode: python app.py --mode grpcserver --host 127.0.0.1 --port 50051
- For GraphQL server mode: python app.py --mode graphqlserver --host 127.0.0.1 --port 8000
"""

import argparse
import os
import sys
import logging

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.startup_mode.cli_mode import command_line_mode
from src.startup_mode.grpc_server_mode import grpc_server_mode
from src.startup_mode.graphql_server_mode import graphql_server_mode
from src.config.config import config

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description='Python app with three modes: command line, gRPC server mode, and GraphQL server mode.')
    parser.add_argument('--mode', choices=['commandline', 'grpcserver', 'graphqlserver'], help='Select the mode to run the app', required=True)
    parser.add_argument('--host', help='Server hostname', default='127.0.0.1')
    parser.add_argument('--port', type=int, help='Server port', default=8000)

    return parser.parse_args()

def main():
    args = parse_command_line_arguments()
    
    if args.mode == 'commandline':
        command_line_mode(config)
    elif args.mode == 'grpcserver':
        grpc_server_mode()
    elif args.mode == 'graphqlserver':
        graphql_server_mode(config, args.host, args.port)
    else:
        print("Invalid mode selected.")
        sys.exit(1)

if __name__ == "__main__":
    main()