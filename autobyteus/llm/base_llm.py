from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator, Type, Dict, Union
import logging

from autobyteus.llm.extensions.token_usage_tracking_extension import TokenUsageTrackingExtension
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.extensions.base_extension import LLMExtension
from autobyteus.llm.extensions.extension_registry import ExtensionRegistry
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.user_message import LLMUserMessage

class BaseLLM(ABC):
    DEFAULT_SYSTEM_MESSAGE = "You are a helpful assistant"

    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not isinstance(model, LLMModel):
            raise TypeError(f"Expected LLMModel, got {type(model)}")
        if not isinstance(llm_config, LLMConfig):
            raise TypeError(f"Expected LLMConfig, got {type(llm_config)}")
            
        self.model = model
        self.config = llm_config
        self._extension_registry = ExtensionRegistry()

        self._token_usage_extension: TokenUsageTrackingExtension = self.register_extension(TokenUsageTrackingExtension)

        self.messages: List[Message] = []
        self.system_message = self.config.system_message or self.DEFAULT_SYSTEM_MESSAGE
        self.add_system_message(self.system_message)

    @property
    def latest_token_usage(self):
        return self._token_usage_extension.latest_token_usage

    def register_extension(self, extension_class: Type[LLMExtension]) -> LLMExtension:
        extension = extension_class(self)
        self._extension_registry.register(extension)
        return extension

    def unregister_extension(self, extension: LLMExtension) -> None:
        self._extension_registry.unregister(extension)

    def get_extension(self, extension_class: Type[LLMExtension]) -> Optional[LLMExtension]:
        return self._extension_registry.get(extension_class)

    def add_system_message(self, message: str):
        self.messages.append(Message(MessageRole.SYSTEM, content=message))

    def add_user_message(self, user_message: LLMUserMessage):
        """
        Adds a user message to history, converting from LLMUserMessage to Message.
        """
        msg = Message(
            role=MessageRole.USER,
            content=user_message.content,
            image_urls=user_message.image_urls,
            audio_urls=user_message.audio_urls,
            video_urls=user_message.video_urls
        )
        self.messages.append(msg)
        self._trigger_on_user_message_added(msg)

    def add_assistant_message(self,
                              content: Optional[str],
                              reasoning_content: Optional[str] = None,
                              image_urls: Optional[List[str]] = None,
                              audio_urls: Optional[List[str]] = None,
                              video_urls: Optional[List[str]] = None):
        """
        Adds a multimodal assistant message to the conversation history.
        """
        msg = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            reasoning_content=reasoning_content,
            image_urls=image_urls,
            audio_urls=audio_urls,
            video_urls=video_urls
        )
        self.messages.append(msg)
        self._trigger_on_assistant_message_added(msg)

    def configure_system_prompt(self, new_system_prompt: str):
        if not new_system_prompt or not isinstance(new_system_prompt, str):
            logging.warning("Attempted to configure an empty or invalid system prompt. No changes made.")
            return

        self.system_message = new_system_prompt
        self.config.system_message = new_system_prompt

        system_message_found = False
        for i, msg in enumerate(self.messages):
            if msg.role == MessageRole.SYSTEM:
                self.messages[i] = Message(MessageRole.SYSTEM, new_system_prompt)
                system_message_found = True
                logging.debug(f"Replaced existing system message at index {i}.")
                break
        
        if not system_message_found:
            self.messages.insert(0, Message(MessageRole.SYSTEM, new_system_prompt))
            logging.debug("No existing system message found, inserted new one at the beginning.")
        
        logging.info(f"LLM instance system prompt updated. New prompt length: {len(new_system_prompt)}")

    def _trigger_on_user_message_added(self, message: Message):
        for extension in self._extension_registry.get_all():
            extension.on_user_message_added(message)

    def _trigger_on_assistant_message_added(self, message: Message):
        for extension in self._extension_registry.get_all():
            extension.on_assistant_message_added(message)

    async def _execute_before_hooks(self, user_message: LLMUserMessage, **kwargs) -> None:
        for extension in self._extension_registry.get_all():
            await extension.before_invoke(user_message, **kwargs)

    async def _execute_after_hooks(self, user_message: LLMUserMessage, response: CompleteResponse = None, **kwargs) -> None:
        for extension in self._extension_registry.get_all():
            await extension.after_invoke(user_message, response, **kwargs)

    async def send_user_message(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        await self._execute_before_hooks(user_message, **kwargs)
        response = await self._send_user_message_to_llm(user_message, **kwargs)
        await self._execute_after_hooks(user_message, response, **kwargs)
        return response

    async def stream_user_message(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        await self._execute_before_hooks(user_message, **kwargs)

        accumulated_content = ""
        accumulated_reasoning = ""
        final_chunk = None
        
        async for chunk in self._stream_user_message_to_llm(user_message, **kwargs):
            if chunk.content:
                accumulated_content += chunk.content
            if chunk.reasoning:
                accumulated_reasoning += chunk.reasoning

            if chunk.is_complete:
                final_chunk = chunk
            yield chunk

        complete_response = CompleteResponse(
            content=accumulated_content,
            reasoning=accumulated_reasoning if accumulated_reasoning else None,
            usage=final_chunk.usage if final_chunk else None
        )
        
        await self._execute_after_hooks(user_message, complete_response, **kwargs)

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        """
        Abstract method for sending a user message to an LLM. Must be implemented by subclasses.
        
        Args:
            user_message (LLMUserMessage): The user message object.
            **kwargs: Additional arguments for LLM-specific usage.
            
        Returns:
            CompleteResponse: The complete response from the LLM.
        """
        pass

    @abstractmethod
    async def _stream_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        """
        Abstract method for streaming a user message response from the LLM. Must be implemented by subclasses.
        
        Args:
            user_message (LLMUserMessage): The user message object.
            **kwargs: Additional arguments for LLM-specific usage.
            
        Yields:
            AsyncGenerator[ChunkResponse, None]: Streaming chunks from the LLM response.
        """
        pass

    async def cleanup(self):
        for extension in self._extension_registry.get_all():
            await extension.cleanup()
        self._extension_registry.clear()
        self.messages = []
