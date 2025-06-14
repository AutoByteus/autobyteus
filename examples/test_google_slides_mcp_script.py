#!/usr/bin/env python3
"""
Real Google Slides MCP (Machine Communication Protocol) Script
This script acts as a stdio-based server that bridges AutoByteUs to the Google Slides API.
It uses pre-configured OAuth credentials from environment variables.
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
def send_message(message: Dict[str, Any]):
    """Sends a JSON message to stdout."""
    try:
        json_message = json.dumps(message)
        sys.stdout.write(json_message + "\n")
        sys.stdout.flush()
        logger.debug(f"Sent message: {json_message[:200]}...")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")

async def process_message(message: Dict[str, Any]):
    """Processes a single incoming MCP message."""
    msg_type = message.get("type")
    request_id = message.get("id")

    if not request_id:
        logger.warning(f"Received message without an 'id': {message}")
        return

    try:
        if msg_type == "list_tools":
            response_payload = {
                "type": "list_tools_result",
                "id": request_id,
                "tools": list(TOOL_DEFS.values()),
            }
            send_message(response_payload)
        
        elif msg_type == "call_tool":
            tool_name = message.get("tool")
            params = message.get("parameters", {})
            
            if tool_name == "create_presentation":
                result_content = await create_presentation(**params)
            elif tool_name == "get_presentation":
                result_content = await get_presentation(**params)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            response_payload = {
                "type": "call_tool_result",
                "id": request_id,
                "tool_name": tool_name,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result_content)}]
                }
            }
            send_message(response_payload)
        else:
            raise ValueError(f"Unsupported message type: {msg_type}")

    except Exception as e:
        logger.error(f"Error processing request {request_id} ({msg_type}): {e}", exc_info=True)
        error_response = {
            "type": "call_tool_result",
            "id": request_id,
            "tool_name": message.get("tool"),
            "error": {"message": str(e)}
        }
        send_message(error_response)


async def main():
    """Main loop to read from stdin and process messages."""
    logger.info("Google Slides MCP server started. Waiting for messages on stdin...")
    loop = asyncio.get_event_loop()
    
    async def read_stdin():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        return reader

    stdin_reader = await read_stdin()
    while not stdin_reader.at_eof():
        line_bytes = await stdin_reader.readline()
        if not line_bytes:
            continue
        line = line_bytes.decode('utf-8').strip()
        if not line:
            continue
        
        logger.debug(f"Received raw message: {line}")
        try:
            message = json.loads(line)
            await process_message(message)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from stdin: {line}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP server shutting down.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred in the MCP server: {e}", exc_info=True)
        sys.exit(1)
