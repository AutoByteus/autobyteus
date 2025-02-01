from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator, Type, Dict, Union

from autobyteus.llm.extensions.token_usage_tracking_extension import TokenUsageTrackingExtension
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.extensions.base_extension import LLMExtension
from autobyteus.llm.extensions.extension_registry import ExtensionRegistry
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse

class BaseLLM(ABC):
    DEFAULT_SYSTEM_MESSAGE = "You are a helpful assistant"

    def __init__(self, model: LLMModel, system_message: Optional[str] = None, custom_config: LLMConfig = None):
        """
        Base class for all LLMs. Provides core messaging functionality
        and extension support.

        Args:
            model (LLMModel): An LLMModel enum value.
            system_message (str, optional): An initial system message.
            custom_config (LLMConfig, optional): A custom config overriding the default.
        """
        self.model = model
        self.config = custom_config if custom_config else model.default_config
        self._extension_registry = ExtensionRegistry()

        # Register TokenUsageTrackingExtension by default
        self._token_usage_extension: TokenUsageTrackingExtension = self.register_extension(TokenUsageTrackingExtension)

        self.messages: List[Message] = []
        self.system_message = system_message if system_message is not None else self.DEFAULT_SYSTEM_MESSAGE
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

    def add_user_message(self, message: Union[str, List[Dict]]):
        """
        Add a user message to the conversation history.

        Args:
            message (Union[str, List[Dict]]): The user message content.
        """
        msg = Message(MessageRole.USER, message)
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

    async def _execute_before_hooks(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> None:
        """
        Execute all registered before_invoke hooks.
        """
        for extension in self._extension_registry.get_all():
            await extension.before_invoke(user_message, file_paths, **kwargs)

    async def _execute_after_hooks(self, user_message: str, file_paths: Optional[List[str]] = None, response: CompleteResponse = None, **kwargs) -> None:
        """
        Execute all registered after_invoke hooks.
        
        Args:
            user_message (str): The original user message
            file_paths (Optional[List[str]]): Any file paths used in the request
            response (CompleteResponse): The complete response from the LLM
            **kwargs: Additional arguments for LLM-specific usage
        """
        for extension in self._extension_registry.get_all():
            await extension.after_invoke(user_message, file_paths, response, **kwargs)

    async def send_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        """
        Sends a user message to the LLM and returns the LLM's response.

        Args:
            user_message (str): The text input from the user.
            file_paths (List[str], optional): A list of file paths for additional context.
            **kwargs: Additional arguments for LLM-specific usage.

        Returns:
            str: The response from the LLM.
        """
        await self._execute_before_hooks(user_message, file_paths, **kwargs)
        response = await self._send_user_message_to_llm(user_message, file_paths, **kwargs)
        await self._execute_after_hooks(user_message, file_paths, response, **kwargs)
        return response.content

    async def stream_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Streams the LLM response token by token.

        Args:
            user_message (str): The text input from the user.
            file_paths (List[str], optional): A list of file paths for additional context.
            **kwargs: Additional arguments for LLM-specific usage.

        Yields:
            AsyncGenerator[str, None]: Tokens from the LLM response.
        """
        await self._execute_before_hooks(user_message, file_paths, **kwargs)

        accumulated_content = ""
        final_chunk = None
        
        async for chunk in self._stream_user_message_to_llm(user_message, file_paths, **kwargs):
            accumulated_content += chunk.content
            if chunk.is_complete:
                final_chunk = chunk
            yield chunk.content

        # Create a CompleteResponse from the accumulated content and final chunk's usage
        complete_response = CompleteResponse(
            content=accumulated_content,
            usage=final_chunk.usage if final_chunk else None
        )
        
        await self._execute_after_hooks(user_message, file_paths, complete_response, **kwargs)

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        """
        Abstract method for sending a user message to an LLM. Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _stream_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        """
        Abstract method for streaming a user message response from the LLM. Must be implemented by subclasses.
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
