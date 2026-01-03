# file: autobyteus/autobyteus/agent/handlers/llm_user_message_ready_event_handler.py
import logging
import traceback
import uuid
from typing import TYPE_CHECKING, cast, Optional, List

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMUserMessageReadyEvent, LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent 
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.agent.streaming.streaming_response_handler import StreamingResponseHandler
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.agent.streaming.parser.json_parsing_strategies.registry import get_json_tool_parsing_profile
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.tool_invocation import ToolInvocationTurn
from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.tool_call_format import resolve_tool_call_format

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class LLMUserMessageReadyEventHandler(AgentEventHandler): 
    """
    Handles LLMUserMessageReadyEvents by sending the prepared LLMUserMessage 
    to the LLM, passing the stream through StreamingResponseHandler for safe parsing,
    emitting filtered chunks via the notifier, and finally enqueuing the complete response.
    """

    def __init__(self):
        logger.info("LLMUserMessageReadyEventHandler initialized.") 

    async def handle(self,
                     event: LLMUserMessageReadyEvent, 
                     context: 'AgentContext') -> None:
        if not isinstance(event, LLMUserMessageReadyEvent): 
            logger.warning(f"LLMUserMessageReadyEventHandler received non-LLMUserMessageReadyEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id 
        if context.state.llm_instance is None: 
            error_msg = f"Agent '{agent_id}' received LLMUserMessageReadyEvent but LLM instance is not yet initialized."
            logger.critical(error_msg)
            if context.status_manager and context.status_manager.notifier:
                context.status_manager.notifier.notify_agent_error_output_generation( # USE RENAMED METHOD
                    error_source="LLMUserMessageReadyEventHandler.pre_llm_check",
                    error_message=error_msg
                )
            raise RuntimeError(error_msg) 

        llm_user_message: LLMUserMessage = event.llm_user_message
        logger.info(f"Agent '{agent_id}' handling LLMUserMessageReadyEvent: '{llm_user_message.content}'") 
        logger.debug(f"Agent '{agent_id}' preparing to send full message to LLM:\n---\n{llm_user_message.content}\n---")
        
        context.state.add_message_to_history({"role": "user", "content": llm_user_message.content})

        # Initialize aggregators
        complete_response_text = ""
        complete_reasoning_text = ""
        token_usage: Optional[TokenUsage] = None
        complete_image_urls: List[str] = []
        complete_audio_urls: List[str] = []
        complete_video_urls: List[str] = []
        
        # Get notifier for emitting events
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.status_manager:
            notifier = context.status_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in LLMUserMessageReadyEventHandler. Cannot emit chunk events.")

        # Callback for segment events from streaming parser
        def emit_segment_event(event: SegmentEvent):
            if notifier:
                try:
                    notifier.notify_agent_segment_event(event.to_dict())
                except Exception as e:
                    logger.error(f"Agent '{agent_id}': Error notifying segment event: {e}", exc_info=True)

        # Create parser config from agent configuration
        parse_tool_calls = bool(context.config.tools)  # Enable tool parsing if agent has tools
        provider = context.state.llm_instance.model.provider if context.state.llm_instance else None
        json_profile = get_json_tool_parsing_profile(provider)
        segment_id_prefix = f"turn_{uuid.uuid4().hex}:"
        parser_config = ParserConfig(
            parse_tool_calls=parse_tool_calls,
            json_tool_patterns=json_profile.signature_patterns,
            json_tool_parser=json_profile.parser,
            segment_id_prefix=segment_id_prefix,
        )

        format_override = context.config.tool_call_format or resolve_tool_call_format()
        if format_override in {"xml", "json", "sentinel", "native"}:
            parser_name = format_override
        else:
            parser_name = "xml"
        
        # Initialize Streaming Response Handler with config and callback
        streaming_handler = StreamingResponseHandler(
            on_segment_event=emit_segment_event,
            config=parser_config,
            parser_name=parser_name,
        )

        # State for manual reasoning parts (since they might come from outside the parser)
        current_reasoning_part_id = None

        try:
            async for chunk_response in context.state.llm_instance.stream_user_message(llm_user_message):
                if not isinstance(chunk_response, ChunkResponse): 
                    logger.warning(f"Agent '{agent_id}' received unexpected chunk type: {type(chunk_response)} during LLM stream. Expected ChunkResponse.")
                    continue

                # Aggregate full raw content
                if chunk_response.content:
                    complete_response_text += chunk_response.content
                if chunk_response.reasoning:
                    complete_reasoning_text += chunk_response.reasoning

                # Collect usage and media from final chunks
                if chunk_response.is_complete:
                    if chunk_response.usage:
                        token_usage = chunk_response.usage
                        logger.debug(f"Agent '{agent_id}' received final chunk with token usage: {token_usage}")
                    if chunk_response.image_urls:
                        complete_image_urls.extend(chunk_response.image_urls)
                    if chunk_response.audio_urls:
                        complete_audio_urls.extend(chunk_response.audio_urls)
                    if chunk_response.video_urls:
                        complete_video_urls.extend(chunk_response.video_urls)

                # Handle Reasoning (Manual Segment Management)
                if chunk_response.reasoning:
                    if current_reasoning_part_id is None:
                        current_reasoning_part_id = f"{segment_id_prefix}reasoning_{uuid.uuid4().hex}"
                        # Emit SEGMENT_START for reasoning
                        start_event = SegmentEvent.start(
                            segment_id=current_reasoning_part_id,
                            segment_type=SegmentType.REASONING
                        )
                        emit_segment_event(start_event)
                    
                    # Emit SEGMENT_CONTENT for reasoning delta
                    content_event = SegmentEvent.content(
                        segment_id=current_reasoning_part_id,
                        delta=chunk_response.reasoning
                    )
                    emit_segment_event(content_event)

                # Handle Content (Through Parser)
                if chunk_response.content:
                    # If we switch to content and have an open reasoning part, we could close it,
                    # but some models might interleave. For now, we'll keep it open until the end 
                    # or if we want to enforce structure we could close it here. 
                    # Let's keep it simple: strict separation isn't guaranteed by all providers.
                    streaming_handler.feed(chunk_response.content)

            # End of stream loop

            # Finalize the stream parser to get any held-back content
            streaming_handler.finalize()

            # After finalization, enqueue any parsed tool invocations.
            if parse_tool_calls:
                tool_invocations = streaming_handler.get_all_invocations()
                if tool_invocations:
                    context.state.active_multi_tool_call_turn = ToolInvocationTurn(
                        invocations=tool_invocations
                    )
                    logger.info(
                        "Agent '%s': Parsed %d tool invocations from streaming parser.",
                        agent_id,
                        len(tool_invocations),
                    )
                    for invocation in tool_invocations:
                        await context.input_event_queues.enqueue_tool_invocation_request(
                            PendingToolInvocationEvent(tool_invocation=invocation)
                        )

            # Close any open reasoning segment
            if current_reasoning_part_id:
                end_event = SegmentEvent.end(segment_id=current_reasoning_part_id)
                emit_segment_event(end_event)

            logger.debug(f"Agent '{agent_id}' LLM stream completed. Full response length: {len(complete_response_text)}.")
            if complete_reasoning_text:
                logger.debug(f"Agent '{agent_id}' aggregated full LLM reasoning.")
            
        except Exception as e:
            logger.error(f"Agent '{agent_id}' error during LLM stream: {e}", exc_info=True)
            error_message_for_output = f"Error processing your request with the LLM: {str(e)}"
            
            logger.warning(f"Agent '{agent_id}' LLM stream error. Error message for output: {error_message_for_output}")
            context.state.add_message_to_history({"role": "assistant", "content": error_message_for_output, "is_error": True})
            
            if notifier:
                try:
                    notifier.notify_agent_error_output_generation( 
                        error_source="LLMUserMessageReadyEventHandler.stream_user_message",
                        error_message=error_message_for_output,
                        error_details=traceback.format_exc()
                    )
                except Exception as e_notify_err: 
                    logger.error(f"Agent '{agent_id}': Error notifying agent output error or chunk stream end after LLM stream failure: {e_notify_err}", exc_info=True)

            complete_response_on_error = CompleteResponse(content=error_message_for_output, usage=None)
            llm_complete_event_on_error = LLMCompleteResponseReceivedEvent(
                complete_response=complete_response_on_error,
                is_error=True 
            )
            await context.input_event_queues.enqueue_internal_system_event(llm_complete_event_on_error)
            logger.info(f"Agent '{agent_id}' enqueued LLMCompleteResponseReceivedEvent with error details.")
            return 

        # Add message to history
        history_entry = {"role": "assistant", "content": complete_response_text}
        if complete_reasoning_text:
            history_entry["reasoning"] = complete_reasoning_text
        if complete_image_urls:
            history_entry["image_urls"] = complete_image_urls
        if complete_audio_urls:
            history_entry["audio_urls"] = complete_audio_urls
        if complete_video_urls:
            history_entry["video_urls"] = complete_video_urls
        context.state.add_message_to_history(history_entry)
        
        # Create complete response
        complete_response_obj = CompleteResponse(
            content=complete_response_text,
            reasoning=complete_reasoning_text,
            usage=token_usage,
            image_urls=complete_image_urls,
            audio_urls=complete_audio_urls,
            video_urls=complete_video_urls
        )
        llm_complete_event = LLMCompleteResponseReceivedEvent(
            complete_response=complete_response_obj
        )
        await context.input_event_queues.enqueue_internal_system_event(llm_complete_event)
        logger.info(f"Agent '{agent_id}' enqueued LLMCompleteResponseReceivedEvent from LLMUserMessageReadyEventHandler.")
