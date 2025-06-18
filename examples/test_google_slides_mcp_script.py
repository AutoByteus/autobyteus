#!/usr/bin/env python3
"""
Real Google Slides MCP (Machine Communication Protocol) Script
This script acts as a stdio-based server that bridges AutoByteUs to the Google Slides API.
It uses pre-configured OAuth credentials from environment variables.
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Ensure the project root is in the Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# --- Logging Setup ---
# Log to stderr to avoid interfering with stdout (which is for MCP messages)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MCP_SERVER] - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Tool Definitions ---
TOOL_DEFS = {
    "create_presentation": {
        "name": "create_presentation",
        "description": "Creates a new Google Slides presentation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The title for the new presentation."},
                "user_google_email": {"type": "string", "description": "The user's Google email address for whom the action is performed. This is for logging and accountability."},
            },
            "required": ["title", "user_google_email"],
        },
    },
    "get_presentation": {
        "name": "get_presentation",
        "description": "Gets details about a Google Slides presentation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "presentation_id": {"type": "string", "description": "The ID of the presentation to retrieve."},
                "user_google_email": {"type": "string", "description": "The user's Google email address for whom the action is performed. This is for logging and accountability."},
            },
            "required": ["presentation_id", "user_google_email"],
        },
    },
    "batch_update_presentation": {
        "name": "batch_update_presentation",
        "description": "Applies one or more updates to the presentation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "presentation_id": {"type": "string", "description": "The ID of the presentation to update."},
                "user_google_email": {"type": "string", "description": "The user's Google email address for whom the action is performed. This is for logging and accountability."},
                "requests": {"type": "array", "description": "A list of update requests to apply to the presentation."},
            },
            "required": ["presentation_id", "user_google_email", "requests"],
        },
    },
}


# --- Google Auth ---
def get_credentials() -> Credentials:
    """Creates Google API credentials from environment variables."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        msg = "Missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or GOOGLE_REFRESH_TOKEN environment variables."
        logger.critical(msg)
        raise ValueError(msg)

    scopes = ['https://www.googleapis.com/auth/presentations']

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes
    )
    try:
        creds.refresh(Request())
        logger.info("Successfully refreshed Google API credentials.")
        return creds
    except Exception as e:
        logger.error(f"Failed to refresh Google credentials: {e}", exc_info=True)
        raise


# --- Tool Implementations ---
async def create_presentation(title: str, user_google_email: str) -> Dict[str, Any]:
    """Implements the create_presentation tool logic."""
    logger.info(f"Executing create_presentation for user '{user_google_email}' with title '{title}'")
    try:
        creds = await asyncio.to_thread(get_credentials)
        service = build('slides', 'v1', credentials=creds)
        
        body = {'title': title}
        presentation = await asyncio.to_thread(
            service.presentations().create(body=body).execute
        )
        
        presentation_id = presentation.get('presentationId')
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        
        result = {
            "status": "success",
            "message": f"Presentation '{title}' created successfully for {user_google_email}.",
            "presentationId": presentation_id,
            "presentationUrl": presentation_url,
        }
        logger.info(f"Successfully created presentation ID: {presentation_id}")
        return result
        
    except HttpError as error:
        logger.error(f"API HttpError creating presentation: {error}", exc_info=True)
        raise Exception(f"API error: {error.reason}. Ensure credentials are valid and have permissions.")
    except Exception as e:
        logger.error(f"Unexpected error creating presentation: {e}", exc_info=True)
        raise

async def batch_update_presentation(presentation_id: str, user_google_email: str, requests: list) -> Dict[str, Any]:
    """Implements the batch_update_presentation tool logic."""
    logger.info(f"Executing batch_update_presentation for user '{user_google_email}' with ID '{presentation_id}'")
    try:
        creds = await asyncio.to_thread(get_credentials)
        service = build('slides', 'v1', credentials=creds)
        
        body = {'requests': requests}
        result = await asyncio.to_thread(
            service.presentations().batchUpdate(
                presentationId=presentation_id, 
                body=body
            ).execute
        )
        
        response = {
            "status": "success",
            "message": f"Successfully applied {len(requests)} updates to presentation for {user_google_email}.",
            "presentationId": presentation_id,
            "replies": result.get('replies', [])
        }
        logger.info(f"Successfully applied batch updates to presentation ID: {presentation_id}")
        return response
        
    except HttpError as error:
        logger.error(f"API HttpError updating presentation: {error}", exc_info=True)
        raise Exception(f"API error: {error.reason}. Check if presentation ID is correct and you have access.")
    except Exception as e:
        logger.error(f"Unexpected error updating presentation: {e}", exc_info=True)
        raise

async def get_presentation(presentation_id: str, user_google_email: str) -> Dict[str, Any]:
    """Implements the get_presentation tool logic."""
    logger.info(f"Executing get_presentation for user '{user_google_email}' with ID '{presentation_id}'")
    try:
        creds = await asyncio.to_thread(get_credentials)
        service = build('slides', 'v1', credentials=creds)

        presentation = await asyncio.to_thread(
            service.presentations().get(presentationId=presentation_id).execute
        )
        
        result = {
            "status": "success",
            "message": f"Retrieved details for presentation '{presentation.get('title')}' for {user_google_email}.",
            "presentationId": presentation.get('presentationId'),
            "title": presentation.get('title'),
            "slidesCount": len(presentation.get('slides', [])),
        }
        logger.info(f"Successfully retrieved presentation '{presentation.get('title')}'")
        return result

    except HttpError as error:
        logger.error(f"API HttpError getting presentation: {error}", exc_info=True)
        raise Exception(f"API error: {error.reason}. Check if presentation ID is correct and you have access.")
    except Exception as e:
        logger.error(f"Unexpected error getting presentation: {e}", exc_info=True)
        raise


# --- MCP Server Logic ---
async def send_ws_message(websocket, message: Dict[str, Any]):
    """Sends a JSON message to the WebSocket client."""
    try:
        json_message = json.dumps(message)
        await websocket.send(json_message)
        logger.debug(f"Sent message: {json_message[:200]}...")
    except Exception as e:
        logger.error(f"Failed to send message via WebSocket: {e}")


async def process_rpc_message(websocket, message: Dict[str, Any]):
    """Processes a single incoming JSON-RPC message."""
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params", {})

    if not request_id or not method:
        logger.warning(f"Received invalid RPC message: {message}")
        error_response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}
        await send_ws_message(websocket, error_response)
        return

    logger.info(f"Processing RPC method '{method}' with id '{request_id}'")

    try:
        result_content = None
        if method == "tools/list":
            result_content = list(TOOL_DEFS.values())
        
        elif method == "tools/call":
            tool_name = params.get("tool_name")
            tool_params = params.get("parameters", {})
            
            logger.info(f"Executing tool '{tool_name}' with params: {tool_params}")
            
            if tool_name == "create_presentation":
                result_content = await create_presentation(**tool_params)
            elif tool_name == "get_presentation":
                result_content = await get_presentation(**tool_params)
            elif tool_name == "batch_update_presentation":
                result_content = await batch_update_presentation(**tool_params)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        else:
            raise ValueError(f"Unknown method: {method}")

        response = {"jsonrpc": "2.0", "result": result_content, "id": request_id}
        await send_ws_message(websocket, response)

    except Exception as e:
        logger.error(f"Error processing request {request_id} ({method}): {e}", exc_info=True)
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": str(e)},
            "id": request_id
        }
        await send_ws_message(websocket, error_response)


async def main_stdio():
    """Listens for messages on stdin and processes them."""
    logger.info("Starting MCP server in stdio mode.")
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            if not line:
                logger.info("Stdin closed, exiting.")
                break
            
            # This is a placeholder and won't be used with websockets
            # message = json.loads(line)
            # await process_message(message)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse or process message: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in main_stdio loop: {e}", exc_info=True)
            # Avoid exiting on processing errors
            pass

async def websocket_handler(websocket, path=None):
    """
    Handles a new WebSocket connection.
    The 'path' argument is made optional for compatibility with older
    versions of the 'websockets' library.
    """
    path_info = f"on path '{path}'" if path else ""
    logger.info(f"Connection open from {websocket.remote_address} {path_info}")
    try:
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                await process_rpc_message(websocket, message)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode incoming JSON: {message_str}")
                error_response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
                await send_ws_message(websocket, error_response)
    except Exception as e:
        logger.error(f"Connection handler failed: {e}", exc_info=True)
    finally:
        logger.info(f"Connection closed from {websocket.remote_address}")


async def main_websocket(host: str, port: int):
    """Starts the WebSocket MCP server."""
    # The 'websockets' library is required for this mode.
    try:
        import websockets
    except ImportError:
        logger.critical("The 'websockets' library is required. Please run 'pip install websockets'.")
        sys.exit(1)
        
    logger.info(f"Starting WebSocket MCP server on ws://{host}:{port}")
    
    server = await websockets.serve(
        websocket_handler,
        host,
        port
    )
    
    for sock in server.sockets:
        logger.info(f"server listening on {sock.getsockname()}")

    await server.wait_closed()


def main():
    """Main entry point for the MCP script."""
    logger.info("***** RUNNING MODIFIED MCP SERVER SCRIPT *****")
    parser = argparse.ArgumentParser(description="Google Slides MCP Server.")
    parser.add_argument(
        "--transport",
        type=str,
        default="websocket",
        choices=["stdio", "websocket"],
        help="The communication transport to use."
    )
    parser.add_argument("--host", type=str, default="localhost", help="Host for WebSocket server.")
    parser.add_argument("--port", type=int, default=8765, help="Port for WebSocket server.")
    args = parser.parse_args()

    # Check for required environment variables before starting
    try:
        get_credentials()
        logger.info("Google credentials check passed.")
    except (ValueError, Exception) as e:
        logger.critical(f"Failed to get Google credentials, cannot start server: {e}")
        sys.exit(1)

    loop = asyncio.get_event_loop()
    try:
        if args.transport == "websocket":
            loop.run_until_complete(main_websocket(args.host, args.port))
        elif args.transport == "stdio":
            loop.run_until_complete(main_stdio())
    except KeyboardInterrupt:
        logger.info("Server shut down by user.")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
