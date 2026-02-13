import logging
import queue as standard_queue
from typing import AsyncIterator, Any, TYPE_CHECKING, Optional, Union

from ..events.stream_events import StreamEvent, StreamEventType
from ..events.stream_event_payloads import (
    create_assistant_chunk_data,
    create_assistant_complete_response_data,
    create_tool_interaction_log_entry_data,
    create_agent_status_update_data,
    create_error_event_data,
    create_tool_approval_requested_data,
    create_tool_approved_data,
    create_tool_denied_data,
    create_tool_execution_started_data,
    create_tool_execution_succeeded_data,
    create_tool_execution_failed_data,
    create_segment_event_data,
    create_system_task_notification_data,
    create_inter_agent_message_data,
    create_todo_list_update_data,
    create_artifact_persisted_data,
    create_artifact_updated_data,
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInteractionLogEntryData,
    AgentStatusUpdateData,
    ToolApprovalRequestedData,
    ToolExecutionStartedData,
    ErrorEventData,
    SystemTaskNotificationData,
    InterAgentMessageData,
    ToDoListUpdateData,
    ArtifactPersistedData,
    ArtifactUpdatedData,
    StreamDataPayload,
)
from ..utils.queue_streamer import stream_queue_items
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)

_AES_INTERNAL_SENTINEL = object()


class AgentEventStream(EventEmitter):
    def __init__(self, agent: "Agent"):
        super().__init__()

        from autobyteus.agent.agent import Agent as ConcreteAgent

        if not isinstance(agent, ConcreteAgent):
            raise TypeError(f"AgentEventStream requires an Agent instance, got {type(agent).__name__}.")

        self.agent_id: str = agent.agent_id
        self._generic_stream_event_internal_q: standard_queue.Queue[Union[StreamEvent, object]] = (
            standard_queue.Queue()
        )

        self._notifier: Optional["AgentExternalEventNotifier"] = None
        if agent.context and agent.context.status_manager:
            self._notifier = agent.context.status_manager.notifier

        if not self._notifier:
            logger.error("AgentEventStream for '%s': Notifier not available. No events will be streamed.", self.agent_id)
            return

        self._register_listeners()
        logger.info(
            "AgentEventStream (ID: %s) initialized for agent_id '%s'. Subscribed to notifier.",
            self.object_id,
            self.agent_id,
        )

    def _register_listeners(self):
        all_agent_event_types = [et for et in EventType if et.name.startswith("AGENT_")]
        for event_type in all_agent_event_types:
            self.subscribe_from(self._notifier, event_type, self._handle_notifier_event_sync)

    def _handle_notifier_event_sync(
        self,
        event_type: EventType,
        payload: Optional[Any] = None,
        object_id: Optional[str] = None,
        **kwargs,
    ):
        event_agent_id = kwargs.get("agent_id", self.agent_id)

        typed_payload_for_stream_event: Optional[StreamDataPayload] = None
        stream_event_type_for_generic_stream: Optional[StreamEventType] = None

        try:
            if event_type == EventType.AGENT_STATUS_UPDATED:
                typed_payload_for_stream_event = create_agent_status_update_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.AGENT_STATUS_UPDATED
            elif event_type == EventType.AGENT_DATA_ASSISTANT_CHUNK:
                typed_payload_for_stream_event = create_assistant_chunk_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_CHUNK
            elif event_type == EventType.AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE:
                typed_payload_for_stream_event = create_assistant_complete_response_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ASSISTANT_COMPLETE_RESPONSE
            elif event_type == EventType.AGENT_DATA_TOOL_LOG:
                typed_payload_for_stream_event = create_tool_interaction_log_entry_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_INTERACTION_LOG_ENTRY
            elif event_type == EventType.AGENT_TOOL_APPROVAL_REQUESTED:
                typed_payload_for_stream_event = create_tool_approval_requested_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_APPROVAL_REQUESTED
            elif event_type == EventType.AGENT_TOOL_APPROVED:
                typed_payload_for_stream_event = create_tool_approved_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_APPROVED
            elif event_type == EventType.AGENT_TOOL_DENIED:
                typed_payload_for_stream_event = create_tool_denied_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_DENIED
            elif event_type == EventType.AGENT_TOOL_EXECUTION_STARTED:
                typed_payload_for_stream_event = create_tool_execution_started_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_EXECUTION_STARTED
            elif event_type == EventType.AGENT_TOOL_EXECUTION_SUCCEEDED:
                typed_payload_for_stream_event = create_tool_execution_succeeded_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_EXECUTION_SUCCEEDED
            elif event_type == EventType.AGENT_TOOL_EXECUTION_FAILED:
                typed_payload_for_stream_event = create_tool_execution_failed_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.TOOL_EXECUTION_FAILED
            elif event_type == EventType.AGENT_DATA_SEGMENT_EVENT:
                typed_payload_for_stream_event = create_segment_event_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.SEGMENT_EVENT
            elif event_type == EventType.AGENT_ERROR_OUTPUT_GENERATION:
                typed_payload_for_stream_event = create_error_event_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ERROR_EVENT
            elif event_type == EventType.AGENT_DATA_SYSTEM_TASK_NOTIFICATION_RECEIVED:
                typed_payload_for_stream_event = create_system_task_notification_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.SYSTEM_TASK_NOTIFICATION
            elif event_type == EventType.AGENT_DATA_INTER_AGENT_MESSAGE_RECEIVED:
                typed_payload_for_stream_event = create_inter_agent_message_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.INTER_AGENT_MESSAGE
            elif event_type == EventType.AGENT_DATA_TODO_LIST_UPDATED:
                typed_payload_for_stream_event = create_todo_list_update_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.AGENT_TODO_LIST_UPDATE
            elif event_type == EventType.AGENT_ARTIFACT_PERSISTED:
                typed_payload_for_stream_event = create_artifact_persisted_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ARTIFACT_PERSISTED
            elif event_type == EventType.AGENT_ARTIFACT_UPDATED:
                typed_payload_for_stream_event = create_artifact_updated_data(payload)
                stream_event_type_for_generic_stream = StreamEventType.ARTIFACT_UPDATED
            elif event_type == EventType.AGENT_DATA_TOOL_LOG_STREAM_END:
                pass
            else:
                logger.debug(
                    "AgentEventStream received internal event '%s' with no direct stream mapping.",
                    event_type.name,
                )
        except Exception as exc:
            logger.error(
                "AgentEventStream error processing payload for event '%s': %s",
                event_type.name,
                exc,
                exc_info=True,
            )

        if typed_payload_for_stream_event and stream_event_type_for_generic_stream:
            stream_event = StreamEvent(
                agent_id=event_agent_id,
                event_type=stream_event_type_for_generic_stream,
                data=typed_payload_for_stream_event,
            )
            self._generic_stream_event_internal_q.put(stream_event)

    async def close(self):
        logger.info(
            "AgentEventStream (ID: %s) for '%s': close() called. Unsubscribing all listeners and signaling.",
            self.object_id,
            self.agent_id,
        )
        self.unsubscribe_all_listeners()
        self._generic_stream_event_internal_q.put(_AES_INTERNAL_SENTINEL)

    async def all_events(self) -> AsyncIterator[StreamEvent]:
        async for event in stream_queue_items(
            self._generic_stream_event_internal_q,
            _AES_INTERNAL_SENTINEL,
            f"agent_{self.agent_id}_all_events",
        ):
            yield event

    async def stream_assistant_chunks(self) -> AsyncIterator[AssistantChunkData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.ASSISTANT_CHUNK and isinstance(event.data, AssistantChunkData):
                yield event.data

    async def stream_assistant_final_response(self) -> AsyncIterator[AssistantCompleteResponseData]:
        async for event in self.all_events():
            if (
                event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE
                and isinstance(event.data, AssistantCompleteResponseData)
            ):
                yield event.data

    async def stream_tool_logs(self) -> AsyncIterator[ToolInteractionLogEntryData]:
        async for event in self.all_events():
            if (
                event.event_type == StreamEventType.TOOL_INTERACTION_LOG_ENTRY
                and isinstance(event.data, ToolInteractionLogEntryData)
            ):
                yield event.data

    async def stream_status_updates(self) -> AsyncIterator[AgentStatusUpdateData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.AGENT_STATUS_UPDATED and isinstance(event.data, AgentStatusUpdateData):
                yield event.data

    async def stream_tool_approval_requests(self) -> AsyncIterator[ToolApprovalRequestedData]:
        async for event in self.all_events():
            if (
                event.event_type == StreamEventType.TOOL_APPROVAL_REQUESTED
                and isinstance(event.data, ToolApprovalRequestedData)
            ):
                yield event.data

    async def stream_tool_execution_started(self) -> AsyncIterator[ToolExecutionStartedData]:
        async for event in self.all_events():
            if (
                event.event_type == StreamEventType.TOOL_EXECUTION_STARTED
                and isinstance(event.data, ToolExecutionStartedData)
            ):
                yield event.data

    async def stream_errors(self) -> AsyncIterator[ErrorEventData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.ERROR_EVENT and isinstance(event.data, ErrorEventData):
                yield event.data

    async def stream_system_task_notifications(self) -> AsyncIterator[SystemTaskNotificationData]:
        async for event in self.all_events():
            if (
                event.event_type == StreamEventType.SYSTEM_TASK_NOTIFICATION
                and isinstance(event.data, SystemTaskNotificationData)
            ):
                yield event.data

    async def stream_inter_agent_messages(self) -> AsyncIterator[InterAgentMessageData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.INTER_AGENT_MESSAGE and isinstance(event.data, InterAgentMessageData):
                yield event.data

    async def stream_todo_updates(self) -> AsyncIterator[ToDoListUpdateData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.AGENT_TODO_LIST_UPDATE and isinstance(event.data, ToDoListUpdateData):
                yield event.data

    async def stream_artifact_persisted(self) -> AsyncIterator[ArtifactPersistedData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.ARTIFACT_PERSISTED and isinstance(event.data, ArtifactPersistedData):
                yield event.data

    async def stream_artifact_updated(self) -> AsyncIterator[ArtifactUpdatedData]:
        async for event in self.all_events():
            if event.event_type == StreamEventType.ARTIFACT_UPDATED and isinstance(event.data, ArtifactUpdatedData):
                yield event.data
