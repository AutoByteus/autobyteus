# file: autobyteus/autobyteus/rpc/protocol.py
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, validator
import uuid

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """Type of the ProtocolMessage."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    EVENT = "event"  # For server-pushed events, e.g., via SSE

class RequestType(str, Enum):
    """Specific method/type for a 'request' message."""
    DISCOVER_CAPABILITIES = "discover_capabilities"
    INVOKE_METHOD = "invoke_method"
    REQUEST_STREAM_DOWNLOAD = "request_stream_download" # New request type for stream download
    # Other specific control messages can be added here

class ResponseType(str, Enum):
    """Specific type for a 'response' message, often mirroring RequestType."""
    CAPABILITIES_RESPONSE = "capabilities_response"
    METHOD_RESULT = "method_result"
    ACKNOWLEDGEMENT = "acknowledgement" # Generic ack
    STREAM_DOWNLOAD_READY = "stream_download_ready" # New response type for stream download

class EventType(str, Enum):
    """Specific type for an 'event' message (server-pushed)."""
    AGENT_OUTPUT_CHUNK = "agent_output_chunk"
    AGENT_FINAL_MESSAGE = "agent_final_message"
    AGENT_STATUS_UPDATE = "agent_status_update"
    TOOL_LOG_ENTRY = "tool_log_entry"
    # Other event types

class ErrorCode(Enum):
    """Standard error codes for RPC communication."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Custom server errors: -32000 to -32099
    SERVER_ERROR_AGENT_PROCESSING_FAILED = -32000
    SERVER_ERROR_CAPABILITY_DISCOVERY_FAILED = -32001
    SERVER_ERROR_UNAUTHORIZED = -32002 # If auth is added
    SERVER_ERROR_TIMEOUT = -32003
    SERVER_ERROR_STREAM_PREPARATION_FAILED = -32004 # For stream download errors
    SERVER_ERROR_STREAM_NOT_FOUND = -32005 # If stream_id is invalid

class ErrorDetails(BaseModel):
    """Structure for error details within a ProtocolMessage."""
    code: Union[ErrorCode, int] # Allow standard ErrorCode or custom int
    message: str
    data: Optional[Any] = None # Optional additional error data

    @validator('code', pre=True)
    def _validate_code(cls, v):
        if isinstance(v, ErrorCode):
            return v.value # Store the integer value of the enum
        if isinstance(v, int):
            return v
        raise ValueError("Error code must be an ErrorCode enum member or an integer.")

class ProtocolMessage(BaseModel):
    """
    Defines the structure for all RPC communications.
    Based on JSON-RPC 2.0 concepts but adapted for AutoByteUs needs.
    """
    # Common fields for all message types
    type: MessageType = Field(..., description="The main type of the message (request, response, error, event).")
    id: Optional[str] = Field(default=None, description="Correlation ID for requests/responses. Can be string or number, UUID for simplicity here.")

    # Fields specific to 'request' type
    method: Optional[Union[RequestType, str]] = Field(default=None, description="Method name for 'request' type (e.g., 'discover_capabilities', 'invoke_method', or a custom agent method name).")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Parameters for the method in 'request' type.")

    # Fields specific to 'response' type
    result: Optional[Any] = Field(default=None, description="Payload of a successful 'response'.")
    response_type: Optional[ResponseType] = Field(default=None, description="Specific type of a 'response', e.g., 'capabilities_response'.")


    # Fields specific to 'error' type (when type is MessageType.ERROR)
    error: Optional[ErrorDetails] = Field(default=None, description="Error details if the message type is 'error'.")

    # Fields specific to 'event' type (server-pushed)
    event_type: Optional[Union[EventType, str]] = Field(default=None, description="Specific type of 'event' (server-pushed).")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Data payload for an 'event'.")
    
    # Auto-generated fields (optional, can be added by sender if needed)
    # timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        use_enum_values = True # Serialize enums to their values
        validate_assignment = True

    @validator('id', pre=True, always=True)
    def set_default_id_for_requests(cls, v, values):
        # Ensure requests have an ID, generate if not provided
        if values.get('type') == MessageType.REQUEST and v is None:
            return str(uuid.uuid4())
        return v
    
    @validator('error')
    def check_error_for_error_type(cls, v, values):
        if values.get('type') == MessageType.ERROR and v is None:
            raise ValueError("Field 'error' is required when message 'type' is ERROR.")
        if values.get('type') != MessageType.ERROR and v is not None:
            raise ValueError("Field 'error' should only be present when message 'type' is ERROR.")
        return v

    @validator('result')
    def check_result_for_response_type(cls, v, values):
        if values.get('type') == MessageType.RESPONSE and values.get('error') is not None:
            raise ValueError("Fields 'result' and 'error' must not coexist in a RESPONSE message.")
        if values.get('type') == MessageType.RESPONSE and v is None and values.get('error') is None:
            # Allow responses with null result explicitly if that's valid (e.g. for simple ack)
            # This validation might be too strict depending on use case.
            # For now, permit null result for acknowledgements and stream_download_ready (which will be populated by server handler)
            if values.get('response_type') not in [ResponseType.ACKNOWLEDGEMENT, ResponseType.STREAM_DOWNLOAD_READY]:
                 logger.debug("Field 'result' is None for a non-acknowledgement/non-stream_download_ready RESPONSE message.")
        return v
        
    @validator('method', 'params')
    def check_request_fields(cls, v, field, values):
        if values.get('type') == MessageType.REQUEST and v is None and field.name == 'method':
            raise ValueError(f"Field '{field.name}' is required when message 'type' is REQUEST.")
        if values.get('type') != MessageType.REQUEST and v is not None:
            raise ValueError(f"Field '{field.name}' should only be present when message 'type' is REQUEST.")
        return v

    @validator('event_type', 'payload')
    def check_event_fields(cls, v, field, values):
        if values.get('type') == MessageType.EVENT and v is None and field.name == 'event_type':
            raise ValueError(f"Field 'event_type' is required when message 'type' is EVENT.")
        # Payload can be optional even for event type
        if values.get('type') != MessageType.EVENT and v is not None:
            raise ValueError(f"Field '{field.name}' should only be present when message 'type' is EVENT.")
        return v

    def to_json_str(self) -> str:
        """Serializes the ProtocolMessage to a JSON string."""
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json_str(cls, json_str: str) -> 'ProtocolMessage':
        """Deserializes a ProtocolMessage from a JSON string."""
        return cls.model_validate_json(json_str)

    # Factory methods for convenience
    @classmethod
    def create_request(cls, method: Union[RequestType, str], params: Optional[Dict[str, Any]] = None, id: Optional[str] = None) -> 'ProtocolMessage':
        return cls(type=MessageType.REQUEST, method=method, params=params or {}, id=id or str(uuid.uuid4()))

    @classmethod
    def create_response(cls, id: str, result: Any, response_type: Optional[ResponseType] = ResponseType.METHOD_RESULT) -> 'ProtocolMessage':
        return cls(type=MessageType.RESPONSE, id=id, result=result, response_type=response_type)

    @classmethod
    def create_error_response(cls, id: Optional[str], code: Union[ErrorCode, int], message: str, data: Optional[Any] = None) -> 'ProtocolMessage':
        actual_code = code.value if isinstance(code, ErrorCode) else code
        return cls(type=MessageType.ERROR, id=id, error=ErrorDetails(code=actual_code, message=message, data=data))

    @classmethod
    def create_event(cls, event_type: Union[EventType, str], payload: Optional[Dict[str, Any]] = None) -> 'ProtocolMessage':
        return cls(type=MessageType.EVENT, event_type=event_type, payload=payload or {})


if __name__ == "__main__": # pragma: no cover
    # Example Usage
    logging.basicConfig(level=logging.DEBUG)

    # Request
    cap_request = ProtocolMessage.create_request(RequestType.DISCOVER_CAPABILITIES)
    logger.info(f"Capability Request: {cap_request.to_json_str()}")

    invoke_request_params = {"tool_name": "calculator", "args": {"operation": "add", "a": 5, "b": 3}}
    invoke_request = ProtocolMessage.create_request(RequestType.INVOKE_METHOD, params=invoke_request_params)
    logger.info(f"Invoke Request: {invoke_request.to_json_str()}")
    
    custom_invoke_req = ProtocolMessage.create_request("custom_agent_method", params={"input_data": "hello"})
    logger.info(f"Custom Invoke Request: {custom_invoke_req.to_json_str()}")

    stream_download_req = ProtocolMessage.create_request(RequestType.REQUEST_STREAM_DOWNLOAD, params={"resource_id": "large_file.dat"})
    logger.info(f"Stream Download Request: {stream_download_req.to_json_str()}")

    # Response
    cap_response_result = {"agent_id": "server_agent_001", "capabilities": ["post_inter_agent_message", "get_status"]}
    cap_response = ProtocolMessage.create_response(id=cap_request.id, result=cap_response_result, response_type=ResponseType.CAPABILITIES_RESPONSE)
    logger.info(f"Capability Response: {cap_response.to_json_str()}")

    invoke_response_result = {"output": 8}
    invoke_response = ProtocolMessage.create_response(id=invoke_request.id, result=invoke_response_result)
    logger.info(f"Invoke Response: {invoke_response.to_json_str()}")

    ack_response = ProtocolMessage.create_response(id=custom_invoke_req.id, result=None, response_type=ResponseType.ACKNOWLEDGEMENT)
    logger.info(f"Ack Response: {ack_response.to_json_str()}")

    stream_download_ready_result = {"stream_id": "uuid-for-stream", "metadata": {"filename": "large_file.dat", "size": 1024000}}
    # Note: download_url would be added by SseServerHandler before sending to client
    stream_download_ready_resp = ProtocolMessage.create_response(id=stream_download_req.id, result=stream_download_ready_result, response_type=ResponseType.STREAM_DOWNLOAD_READY)
    logger.info(f"Stream Download Ready Response (initial): {stream_download_ready_resp.to_json_str()}")


    # Error Response
    error_resp = ProtocolMessage.create_error_response(id=invoke_request.id, code=ErrorCode.METHOD_NOT_FOUND, message="Method not supported by agent.")
    logger.info(f"Error Response: {error_resp.to_json_str()}")
    
    parse_error_resp = ProtocolMessage.create_error_response(id=None, code=ErrorCode.PARSE_ERROR, message="Invalid JSON received.")
    logger.info(f"Parse Error Response (no ID): {parse_error_resp.to_json_str()}")

    stream_error_resp = ProtocolMessage.create_error_response(
        id=stream_download_req.id,
        code=ErrorCode.SERVER_ERROR_STREAM_PREPARATION_FAILED,
        message="Agent failed to prepare the stream for resource 'large_file.dat'."
    )
    logger.info(f"Stream Preparation Error Response: {stream_error_resp.to_json_str()}")

    # Event
    status_event = ProtocolMessage.create_event(EventType.AGENT_STATUS_UPDATE, payload={"status": "running"})
    logger.info(f"Status Event: {status_event.to_json_str()}")
    
    # Test validation
    try:
        invalid_msg = ProtocolMessage(type=MessageType.REQUEST) # Missing method
    except ValueError as e:
        logger.error(f"Validation Error: {e}")

    try:
        invalid_error_msg = ProtocolMessage(type=MessageType.ERROR, id="123") # Missing error field
    except ValueError as e:
        logger.error(f"Validation Error: {e}")

    try:
        error_details_invalid_code = ErrorDetails(code="INVALID_CODE_STR", message="test")
    except ValueError as e:
        logger.error(f"Validation Error (ErrorDetails): {e}")
    
    error_details_valid_int_code = ErrorDetails(code=-32050, message="Custom server error")
    logger.info(f"ErrorDetails with int code: {error_details_valid_int_code.model_dump_json()}")
    assert error_details_valid_int_code.code == -32050
