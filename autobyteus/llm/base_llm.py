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

        self.system_message = self.config.system_message or self.DEFAULT_SYSTEM_MESSAGE

    @property
    def latest_token_usage(self):
        """Get latest token usage. Returns None if token tracking is disabled."""
        if not self._token_usage_extension.is_enabled:
            return None
        return self._token_usage_extension.latest_token_usage

    def register_extension(self, extension_class: Type[LLMExtension]) -> LLMExtension:
        extension = extension_class(self)
        self._extension_registry.register(extension)
        return extension

    def unregister_extension(self, extension: LLMExtension) -> None:
        self._extension_registry.unregister(extension)

    def get_extension(self, extension_class: Type[LLMExtension]) -> Optional[LLMExtension]:
        return self._extension_registry.get(extension_class)

    def _build_user_message(self, user_message: LLMUserMessage) -> Message:
        return Message(
            role=MessageRole.USER,
            content=user_message.content,
            image_urls=user_message.image_urls,
            audio_urls=user_message.audio_urls,
            video_urls=user_message.video_urls,
        )

    def _build_system_message(self) -> Optional[Message]:
        if not self.system_message:
            return None
        return Message(MessageRole.SYSTEM, content=self.system_message)

    def configure_system_prompt(self, new_system_prompt: str):
        if not new_system_prompt or not isinstance(new_system_prompt, str):
            logging.warning("Attempted to configure an empty or invalid system prompt. No changes made.")
            return

        self.system_message = new_system_prompt
        self.config.system_message = new_system_prompt
        logging.info(f"LLM instance system prompt updated. New prompt length: {len(new_system_prompt)}")

    async def _execute_before_hooks(self, messages: List[Message], rendered_payload: Optional[dict] = None, **kwargs) -> None:
        for extension in self._extension_registry.get_all():
            await extension.before_invoke(messages, rendered_payload, **kwargs)

    async def _execute_after_hooks(self, messages: List[Message], response: CompleteResponse = None, **kwargs) -> None:
        for extension in self._extension_registry.get_all():
            await extension.after_invoke(messages, response, **kwargs)

    async def send_messages(
        self,
        messages: List[Message],
        rendered_payload: Optional[dict] = None,
        **kwargs,
    ) -> CompleteResponse:
        await self._execute_before_hooks(messages, rendered_payload, **kwargs)
        response = await self._send_messages_to_llm(messages, **kwargs)
        await self._execute_after_hooks(messages, response, **kwargs)
        return response

    async def stream_messages(
        self,
        messages: List[Message],
        rendered_payload: Optional[dict] = None,
        **kwargs,
    ) -> AsyncGenerator[ChunkResponse, None]:
        await self._execute_before_hooks(messages, rendered_payload, **kwargs)

        accumulated_content = ""
        accumulated_reasoning = ""
        final_chunk = None

        async for chunk in self._stream_messages_to_llm(messages, **kwargs):
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
            usage=final_chunk.usage if final_chunk else None,
        )

        await self._execute_after_hooks(messages, complete_response, **kwargs)

    async def send_user_message(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        messages: List[Message] = []
        system_message = self._build_system_message()
        if system_message:
            messages.append(system_message)
        messages.append(self._build_user_message(user_message))
        return await self.send_messages(messages, **kwargs)

    async def stream_user_message(
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        messages: List[Message] = []
        system_message = self._build_system_message()
        if system_message:
            messages.append(system_message)
        messages.append(self._build_user_message(user_message))
        async for chunk in self.stream_messages(messages, **kwargs):
            yield chunk

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        messages: List[Message] = []
        system_message = self._build_system_message()
        if system_message:
            messages.append(system_message)
        messages.append(self._build_user_message(user_message))
        return await self._send_messages_to_llm(messages, **kwargs)

    async def _stream_user_message_to_llm(
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        messages: List[Message] = []
        system_message = self._build_system_message()
        if system_message:
            messages.append(system_message)
        messages.append(self._build_user_message(user_message))
        async for chunk in self._stream_messages_to_llm(messages, **kwargs):
            yield chunk

    @abstractmethod
    async def _send_messages_to_llm(self, messages: List[Message], **kwargs) -> CompleteResponse:
        """
        Abstract method for sending a list of messages to an LLM. Must be implemented by subclasses.

        Args:
            messages (List[Message]): The message list to send.
            **kwargs: Additional arguments for LLM-specific usage.

        Returns:
            CompleteResponse: The complete response from the LLM.
        """
        pass

    @abstractmethod
    async def _stream_messages_to_llm(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        """
        Abstract method for streaming a response from an LLM. Must be implemented by subclasses.

        Args:
            messages (List[Message]): The message list to send.
            **kwargs: Additional arguments for LLM-specific usage.

        Yields:
            AsyncGenerator[ChunkResponse, None]: Streaming chunks from the LLM response.
        """
        pass

    async def cleanup(self):
        for extension in self._extension_registry.get_all():
            await extension.cleanup()
        self._extension_registry.clear()
