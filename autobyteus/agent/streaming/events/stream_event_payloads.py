import logging
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.agent.status.status_enum import AgentStatus


logger = logging.getLogger(__name__)


class BaseStreamPayload(BaseModel):
    class Config:
        extra = "allow"


class AssistantChunkData(BaseStreamPayload):
    content: str
    reasoning: Optional[str] = None
    is_complete: bool
    usage: Optional[TokenUsage] = None
    image_urls: Optional[List[str]] = None
    audio_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None


class AssistantCompleteResponseData(BaseStreamPayload):
    content: str
    reasoning: Optional[str] = None
    usage: Optional[TokenUsage] = None
    image_urls: Optional[List[str]] = None
    audio_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None


class ToolInteractionLogEntryData(BaseStreamPayload):
    log_entry: str
    tool_invocation_id: str
    tool_name: str


class AgentStatusUpdateData(BaseStreamPayload):
    new_status: AgentStatus
    old_status: Optional[AgentStatus] = None
    trigger: Optional[str] = None
    tool_name: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None


class ErrorEventData(BaseStreamPayload):
    source: str
    message: str
    details: Optional[str] = None


class ToolApprovalRequestedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    arguments: Dict[str, Any]


class ToolApprovedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    reason: Optional[str] = None


class ToolDeniedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None


class ToolExecutionStartedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class ToolExecutionSucceededData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    result: Optional[Any] = None


class ToolExecutionFailedData(BaseStreamPayload):
    invocation_id: str
    tool_name: str
    turn_id: Optional[str] = None
    error: str


class SegmentEventData(BaseStreamPayload):
    event_type: str = Field(alias="type")
    segment_id: str
    segment_type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class SystemTaskNotificationData(BaseStreamPayload):
    sender_id: str
    content: str


class InterAgentMessageData(BaseStreamPayload):
    sender_agent_id: str
    recipient_role_name: str
    content: str
    message_type: str


class ToDoItemData(BaseStreamPayload):
    description: str
    todo_id: str
    status: str


class ToDoListUpdateData(BaseStreamPayload):
    todos: List[ToDoItemData]


class ArtifactPersistedData(BaseStreamPayload):
    artifact_id: str
    path: str
    agent_id: str
    type: str
    workspace_root: Optional[str] = None
    url: Optional[str] = None


class ArtifactUpdatedData(BaseStreamPayload):
    artifact_id: Optional[str] = None
    path: str
    agent_id: str
    type: str
    workspace_root: Optional[str] = None


class EmptyData(BaseStreamPayload):
    pass


StreamDataPayload = Union[
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInteractionLogEntryData,
    AgentStatusUpdateData,
    ErrorEventData,
    ToolApprovalRequestedData,
    ToolApprovedData,
    ToolDeniedData,
    ToolExecutionStartedData,
    ToolExecutionSucceededData,
    ToolExecutionFailedData,
    SegmentEventData,
    SystemTaskNotificationData,
    InterAgentMessageData,
    ToDoListUpdateData,
    ArtifactPersistedData,
    ArtifactUpdatedData,
    EmptyData,
]


def create_assistant_chunk_data(chunk_obj: Any) -> AssistantChunkData:
    usage_data = None
    if hasattr(chunk_obj, "usage"):
        usage_data = getattr(chunk_obj, "usage")
    elif isinstance(chunk_obj, dict) and "usage" in chunk_obj:
        usage_data = chunk_obj.get("usage")

    parsed_usage = None
    if usage_data:
        if isinstance(usage_data, TokenUsage):
            parsed_usage = usage_data
        elif isinstance(usage_data, dict):
            try:
                parsed_usage = TokenUsage(**usage_data)
            except Exception as exc:
                logger.warning(
                    "Could not parse usage dict into TokenUsage for AssistantChunkData: %s. Usage dict: %s",
                    exc,
                    usage_data,
                )
        else:
            logger.warning("Unsupported usage type %s for AssistantChunkData.", type(usage_data))

    if hasattr(chunk_obj, "content") and hasattr(chunk_obj, "is_complete"):
        return AssistantChunkData(
            content=str(getattr(chunk_obj, "content", "")),
            reasoning=getattr(chunk_obj, "reasoning", None),
            is_complete=bool(getattr(chunk_obj, "is_complete", False)),
            usage=parsed_usage,
            image_urls=getattr(chunk_obj, "image_urls", None),
            audio_urls=getattr(chunk_obj, "audio_urls", None),
            video_urls=getattr(chunk_obj, "video_urls", None),
        )

    if isinstance(chunk_obj, dict):
        return AssistantChunkData(
            content=str(chunk_obj.get("content", "")),
            reasoning=chunk_obj.get("reasoning", None),
            is_complete=bool(chunk_obj.get("is_complete", False)),
            usage=parsed_usage,
            image_urls=chunk_obj.get("image_urls", None),
            audio_urls=chunk_obj.get("audio_urls", None),
            video_urls=chunk_obj.get("video_urls", None),
        )

    raise ValueError(f"Cannot create AssistantChunkData from {type(chunk_obj)}")


def create_assistant_complete_response_data(complete_resp_obj: Any) -> AssistantCompleteResponseData:
    usage_data = None
    if hasattr(complete_resp_obj, "usage"):
        usage_data = getattr(complete_resp_obj, "usage")
    elif isinstance(complete_resp_obj, dict) and "usage" in complete_resp_obj:
        usage_data = complete_resp_obj.get("usage")

    parsed_usage = None
    if usage_data:
        if isinstance(usage_data, TokenUsage):
            parsed_usage = usage_data
        elif isinstance(usage_data, dict):
            try:
                parsed_usage = TokenUsage(**usage_data)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Could not parse usage dict into TokenUsage for AssistantCompleteResponseData: %s. Usage dict: %s",
                    exc,
                    usage_data,
                )
        else:  # pragma: no cover
            logger.warning(
                "Unsupported usage type %s for AssistantCompleteResponseData.",
                type(usage_data),
            )

    if hasattr(complete_resp_obj, "content"):
        return AssistantCompleteResponseData(
            content=str(getattr(complete_resp_obj, "content", "")),
            reasoning=getattr(complete_resp_obj, "reasoning", None),
            usage=parsed_usage,
            image_urls=getattr(complete_resp_obj, "image_urls", None),
            audio_urls=getattr(complete_resp_obj, "audio_urls", None),
            video_urls=getattr(complete_resp_obj, "video_urls", None),
        )

    if isinstance(complete_resp_obj, dict):
        return AssistantCompleteResponseData(
            content=str(complete_resp_obj.get("content", "")),
            reasoning=complete_resp_obj.get("reasoning", None),
            usage=parsed_usage,
            image_urls=complete_resp_obj.get("image_urls", None),
            audio_urls=complete_resp_obj.get("audio_urls", None),
            video_urls=complete_resp_obj.get("video_urls", None),
        )

    raise ValueError(f"Cannot create AssistantCompleteResponseData from {type(complete_resp_obj)}")


def create_tool_interaction_log_entry_data(log_data: Any) -> ToolInteractionLogEntryData:
    if isinstance(log_data, dict) and all(k in log_data for k in ["log_entry", "tool_invocation_id", "tool_name"]):
        return ToolInteractionLogEntryData(**log_data)
    raise ValueError(
        f"Cannot create ToolInteractionLogEntryData from {type(log_data)}. "
        "Expected dict with 'log_entry', 'tool_invocation_id', and 'tool_name' keys."
    )


def create_agent_status_update_data(status_data_dict: Any) -> AgentStatusUpdateData:
    if isinstance(status_data_dict, dict):
        return AgentStatusUpdateData(**status_data_dict)
    raise ValueError(f"Cannot create AgentStatusUpdateData from {type(status_data_dict)}")


def create_error_event_data(error_data_dict: Any) -> ErrorEventData:
    if isinstance(error_data_dict, dict):
        return ErrorEventData(**error_data_dict)
    raise ValueError(f"Cannot create ErrorEventData from {type(error_data_dict)}")


def create_tool_approval_requested_data(approval_data_dict: Any) -> ToolApprovalRequestedData:
    if isinstance(approval_data_dict, dict):
        return ToolApprovalRequestedData(**approval_data_dict)
    raise ValueError(f"Cannot create ToolApprovalRequestedData from {type(approval_data_dict)}")


def create_tool_approved_data(approval_data_dict: Any) -> ToolApprovedData:
    if isinstance(approval_data_dict, dict):
        return ToolApprovedData(**approval_data_dict)
    raise ValueError(f"Cannot create ToolApprovedData from {type(approval_data_dict)}")


def create_tool_denied_data(denial_data_dict: Any) -> ToolDeniedData:
    if isinstance(denial_data_dict, dict):
        return ToolDeniedData(**denial_data_dict)
    raise ValueError(f"Cannot create ToolDeniedData from {type(denial_data_dict)}")


def create_tool_execution_started_data(start_data_dict: Any) -> ToolExecutionStartedData:
    if isinstance(start_data_dict, dict):
        return ToolExecutionStartedData(**start_data_dict)
    raise ValueError(f"Cannot create ToolExecutionStartedData from {type(start_data_dict)}")


def create_tool_execution_succeeded_data(success_data_dict: Any) -> ToolExecutionSucceededData:
    if isinstance(success_data_dict, dict):
        return ToolExecutionSucceededData(**success_data_dict)
    raise ValueError(f"Cannot create ToolExecutionSucceededData from {type(success_data_dict)}")


def create_tool_execution_failed_data(error_data_dict: Any) -> ToolExecutionFailedData:
    if isinstance(error_data_dict, dict):
        return ToolExecutionFailedData(**error_data_dict)
    raise ValueError(f"Cannot create ToolExecutionFailedData from {type(error_data_dict)}")


def create_segment_event_data(event_data: Any) -> SegmentEventData:
    if isinstance(event_data, SegmentEventData):
        return event_data
    if isinstance(event_data, dict):
        return SegmentEventData(**event_data)
    raise ValueError(f"Cannot create SegmentEventData from {type(event_data)}")


def create_inter_agent_message_data(msg_data: Any) -> InterAgentMessageData:
    if isinstance(msg_data, dict):
        required_keys = ["sender_agent_id", "recipient_role_name", "content", "message_type"]
        missing = [k for k in required_keys if k not in msg_data]
        if missing:
            raise ValueError(f"InterAgentMessageData missing keys: {missing}")
        return InterAgentMessageData(**msg_data)
    raise ValueError(f"Cannot create InterAgentMessageData from {type(msg_data)}")


def create_system_task_notification_data(notification_data_dict: Any) -> SystemTaskNotificationData:
    if isinstance(notification_data_dict, dict):
        return SystemTaskNotificationData(**notification_data_dict)
    raise ValueError(f"Cannot create SystemTaskNotificationData from {type(notification_data_dict)}")


def create_todo_list_update_data(todo_data_dict: Any) -> ToDoListUpdateData:
    if isinstance(todo_data_dict, dict):
        todos_payload = todo_data_dict.get("todos", [])
        if not isinstance(todos_payload, list):
            raise ValueError("Expected 'todos' to be a list when creating ToDoListUpdateData.")
        todo_items = []
        for todo_entry in todos_payload:
            if not isinstance(todo_entry, dict):
                logger.warning(
                    "Skipping non-dict todo entry when creating ToDoListUpdateData: %r",
                    todo_entry,
                )
                continue
            try:
                todo_items.append(ToDoItemData(**todo_entry))
            except Exception as exc:
                logger.warning(
                    "Failed to parse todo entry into ToDoItemData: %r; error: %s",
                    todo_entry,
                    exc,
                )
        return ToDoListUpdateData(todos=todo_items)
    raise ValueError(f"Cannot create ToDoListUpdateData from {type(todo_data_dict)}")


def create_artifact_persisted_data(data_dict: Any) -> ArtifactPersistedData:
    if isinstance(data_dict, dict):
        return ArtifactPersistedData(**data_dict)
    raise ValueError(f"Cannot create ArtifactPersistedData from {type(data_dict)}")


def create_artifact_updated_data(data_dict: Any) -> ArtifactUpdatedData:
    if isinstance(data_dict, dict):
        return ArtifactUpdatedData(**data_dict)
    raise ValueError(f"Cannot create ArtifactUpdatedData from {type(data_dict)}")
