
from typing import Dict, Optional, List, AsyncGenerator, Tuple
import anthropic
import os
import logging
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class ClaudeLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None, custom_config: LLMConfig = None):
        super().__init__(model=model or LLMModel.CLAUDE_3_5_SONNET_API, system_message=system_message, custom_config=custom_config)
        self.client = self.initialize()
        self.max_tokens = 8000
    
    @classmethod
    def initialize(cls):
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return anthropic.Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")
    
    def _get_non_system_messages(self) -> List[Dict]:
        """
        Returns all messages excluding system messages for Anthropic API compatibility.
        """
        return [msg.to_dict() for msg in self.messages if msg.role != MessageRole.SYSTEM]
    
    def _create_token_usage(self, input_tokens: int, output_tokens: int) -> TokenUsage:
        """Convert Anthropic usage data to TokenUsage format."""
        return TokenUsage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
    
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)

        try:
            response = self.client.messages.create(
                model=self.model.value,
                max_tokens=self.max_tokens,
                temperature=0,
                system=self.system_message,
                messages=self._get_non_system_messages()
            )

            assistant_message = response.content[0].text
            self.add_assistant_message(assistant_message)

            token_usage = self._create_token_usage(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
            
            logger.info(f"Token usage - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except anthropic.APIError as e:
            logger.error(f"Error in Claude API call: {str(e)}")
            raise ValueError(f"Error in Claude API call: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        final_message = None

        try:
            with self.client.messages.stream(
                model=self.model.value,
                max_tokens=self.max_tokens,
                temperature=0,
                system=self.system_message,
                messages=self._get_non_system_messages(),
            ) as stream:
                for event in stream:
                    logger.debug(f"Event Received: {event.type}")
                    
                    if event.type == "message_start":
                        logger.debug(f"Message Start: {event.message}")
                    
                    elif event.type == "content_block_start":
                        logger.debug(f"Content Block Start at index {event.index}: {event.content_block}")
                    
                    elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                        logger.debug(f"Text Delta: {event.delta.text}")
                        complete_response += event.delta.text
                        yield ChunkResponse(
                            content=event.delta.text,
                            is_complete=False
                        )
                    
                    elif event.type == "message_delta":
                        logger.debug(f"Message Delta: Stop Reason - {event.delta.stop_reason}, "
                                   f"Stop Sequence - {event.delta.stop_sequence}")
                    
                    elif event.type == "content_block_stop":
                        logger.debug(f"Content Block Stop at index {event.index}: {event.content_block}")

                # Get final message for token usage
                final_message = stream.get_final_message()
                if final_message:
                    token_usage = self._create_token_usage(
                        final_message.usage.input_tokens,
                        final_message.usage.output_tokens
                    )
                    logger.info(f"Final token usage - Input: {final_message.usage.input_tokens}, "
                               f"Output: {final_message.usage.output_tokens}")
                    yield ChunkResponse(
                        content="",
                        is_complete=True,
                        usage=token_usage
                    )

            self.add_assistant_message(complete_response)
        except anthropic.APIError as e:
            logger.error(f"Error in Claude API streaming: {str(e)}")
            raise ValueError(f"Error in Claude API streaming: {str(e)}")
    
    async def cleanup(self):
        super().cleanup()
