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
        """
        Base class for all LLMs. Provides core messaging functionality
        and extension support.

        Args:
            model (LLMModel): An LLMModel enum value.
            llm_config (LLMConfig): Configuration for the LLM including system message, 
                                   rate limits, token limits, etc.
        """
        if not isinstance(model, LLMModel):
            raise TypeError(f"Expected LLMModel, got {type(model)}")
        if not isinstance(llm_config, LLMConfig):
            raise TypeError(f"Expected LLMConfig, got {type(llm_config)}")
            
        self.model = model
        self.config = llm_config
        self._extension_registry = ExtensionRegistry()

        # Register TokenUsageTrackingExtension by default
        self._token_usage_extension: TokenUsageTrackingExtension = self.register_extension(TokenUsageTrackingExtension)

        self.messages: List[Message] = []
        # Use system_message from config, with fallback to default if not provided
        self.system_message = self.config.system_message or self.DEFAULT_SYSTEM_MESSAGE
        self.add_system_message(self.system_message)

    @property
    def latest_token_usage(self):
        """
        Get the token usage from the last interaction with the LLM.
        
        Returns:
            The token usage information from the last interaction
        """
        return self._token_usage_extension.latest_token_usage

    def register_extension(self, extension_class: Type[LLMExtension]) -> LLMExtension:
        """
        Register a new extension.
        
        Args:
            extension_class: The extension class to instantiate and register
        
        Returns:
            LLMExtension: The instantiated extension
        """
        extension = extension_class(self)
        self._extension_registry.register(extension)
        return extension

    def unregister_extension(self, extension: LLMExtension) -> None:
        """
        Unregister an existing extension.
        
        Args:
            extension (LLMExtension): The extension to unregister
        """
        self._extension_registry.unregister(extension)

    def get_extension(self, extension_class: Type[LLMExtension]) -> Optional[LLMExtension]:
        """
        Get a registered extension by its class.
        
        Args:
            extension_class: The class of the extension to retrieve
            
        Returns:
            Optional[LLMExtension]: The extension instance if found, None otherwise
        """
        return self._extension_registry.get(extension_class)

    def add_system_message(self, message: str):
        """
        Add a system message to the conversation history.

        Args:
            message (str): The system message content.
        """
        self.messages.append(Message(MessageRole.SYSTEM, message))

    def add_user_message(self, user_message: Union[str, List[Dict]]):
        """
        Add a user message to the conversation history.

        Args:
            user_message (Union[str, List[Dict]]): The user message content. Can be a simple string
                                                   or a list of dictionaries for multimodal content.
        """
        msg = Message(MessageRole.USER, user_message) 
        self.messages.append(msg)
        self._trigger_on_user_message_added(msg)

    def add_assistant_message(self, message: str, reasoning_content: Optional[str] = None):
        """
        Add an assistant message to the conversation history.

        Args:
            message (str): The assistant message content.
            reasoning_content (Optional[str]): Optional reasoning content to attach.
        """
        msg = Message(MessageRole.ASSISTANT, message, reasoning_content=reasoning_content)
        self.messages.append(msg)
        self._trigger_on_assistant_message_added(msg)

    def configure_system_prompt(self, new_system_prompt: str):
        """
        Updates the system prompt for the LLM instance after initialization.
        This will replace the existing system message in the conversation history.

        Args:
            new_system_prompt (str): The new system prompt content.
        """
        if not new_system_prompt or not isinstance(new_system_prompt, str):
            logging.warning("Attempted to configure an empty or invalid system prompt. No changes made.")
            return

        self.system_message = new_system_prompt
        self.config.system_message = new_system_prompt

        # Find and update the existing system message, or add a new one if not found.
        system_message_found = False
        for i, msg in enumerate(self.messages):
            if msg.role == MessageRole.SYSTEM:
                self.messages[i] = Message(MessageRole.SYSTEM, new_system_prompt)
                system_message_found = True
                logging.debug(f"Replaced existing system message at index {i}.")
                break
        
        if not system_message_found:
            # If for some reason no system message was there, insert it at the beginning.
            self.messages.insert(0, Message(MessageRole.SYSTEM, new_system_prompt))
            logging.debug("No existing system message found, inserted new one at the beginning.")
        
        logging.info(f"LLM instance system prompt updated. New prompt length: {len(new_system_prompt)}")

    def _trigger_on_user_message_added(self, message: Message):
        """
        Internal helper to invoke the on_user_message_added hook on every extension.

        Args:
            message (Message): The user message that was added
        """
        for extension in self._extension_registry.get_all():
            extension.on_user_message_added(message)

    def _trigger_on_assistant_message_added(self, message: Message):
        """
        Internal helper to invoke the on_assistant_message_added hook on every extension.

        Args:
            message (Message): The assistant message that was added
        """
        for extension in self._extension_registry.get_all():
            extension.on_assistant_message_added(message)

    async def _execute_before_hooks(self, user_message: LLMUserMessage, **kwargs) -> None:
        """
        Execute all registered before_invoke hooks.
        """
        for extension in self._extension_registry.get_all():
            await extension.before_invoke(user_message.content, user_message.image_urls, **kwargs)

    async def _execute_after_hooks(self, user_message: LLMUserMessage, response: CompleteResponse = None, **kwargs) -> None:
        """
        Execute all registered after_invoke hooks.
        
        Args:
            user_message (LLMUserMessage): The user message object
            response (CompleteResponse): The complete response from the LLM
            **kwargs: Additional arguments for LLM-specific usage
        """
        for extension in self._extension_registry.get_all():
            await extension.after_invoke(user_message.content, user_message.image_urls, response, **kwargs)

    async def send_user_message(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        """
        Sends a user message to the LLM and returns the complete LLM response.

        Args:
            user_message (LLMUserMessage): The user message object.
            **kwargs: Additional arguments for LLM-specific usage.

        Returns:
            CompleteResponse: The complete response from the LLM including content and usage.
        """
        await self._execute_before_hooks(user_message, **kwargs)
        response = await self._send_user_message_to_llm(
            user_message.content, 
            user_message.image_urls if user_message.image_urls else None, 
            **kwargs
        )
        await self._execute_after_hooks(user_message, response, **kwargs)
        return response

    async def stream_user_message(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        """
        Streams the LLM response as ChunkResponse objects.

        Args:
            user_message (LLMUserMessage): The user message object.
            **kwargs: Additional arguments for LLM-specific usage.

        Yields:
            AsyncGenerator[ChunkResponse, None]: ChunkResponse objects from the LLM.
        """
        await self._execute_before_hooks(user_message, **kwargs)

        accumulated_content = ""
        final_chunk = None
        
        async for chunk in self._stream_user_message_to_llm(
            user_message.content, 
            user_message.image_urls if user_message.image_urls else None, 
            **kwargs
        ):
            accumulated_content += chunk.content
            if chunk.is_complete:
                final_chunk = chunk
            yield chunk

        # Create a CompleteResponse from the accumulated content and final chunk's usage
        complete_response = CompleteResponse(
            content=accumulated_content,
            usage=final_chunk.usage if final_chunk else None
        )
        
        await self._execute_after_hooks(user_message, complete_response, **kwargs)

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        """
        Abstract method for sending a user message to an LLM. Must be implemented by subclasses.
        
        Args:
            user_message (str): The user message content.
            image_urls (Optional[List[str]]): Optional list of image URLs or file paths.
            **kwargs: Additional arguments for LLM-specific usage.
            
        Returns:
            CompleteResponse: The complete response from the LLM.
        """
        pass

    @abstractmethod
    async def _stream_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        """
        Abstract method for streaming a user message response from the LLM. Must be implemented by subclasses.
        
        Args:
            user_message (str): The user message content.
            image_urls (Optional[List[str]]): Optional list of image URLs or file paths.
            **kwargs: Additional arguments for LLM-specific usage.
            
        Yields:
            AsyncGenerator[ChunkResponse, None]: Streaming chunks from the LLM response.
        """
        pass

    async def cleanup(self):
        """
        Perform cleanup operations for the LLM and all extensions.
        """
        for extension in self._extension_registry.get_all():
            await extension.cleanup()
        self._extension_registry.clear()
        self.messages = []
