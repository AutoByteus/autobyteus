# file: autobyteus/tools/base_tool.py
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Forward reference

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """
    Abstract base class for all tools that an agent can use.
    Tools are designed to perform specific actions or retrieve information.
    """

    def __init__(self):
        """
        Initializes the BaseTool.
        """
        logger.debug(f"BaseTool instance created: {self.__class__.__name__}")

    @abstractmethod
    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        """
        The core execution logic of the tool. Subclasses must implement this method.
        FR9: Accepts AgentContext as the first parameter.

        Args:
            context: The AgentContext providing runtime information, access to LLM,
                     other tools, queues, etc.
            **kwargs: Keyword arguments specific to the tool's operation.

        Returns:
            The result of the tool's execution. The type of this result
            is specific to the tool.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__}._execute must be implemented by subclasses.")

    async def execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        """
        Public method to execute the tool. This method wraps the internal _execute method.
        FR9: Accepts AgentContext as the first parameter.

        It can be extended in the future to include common pre/post execution logic,
        such as input validation, logging, or error handling, if desired.

        Args:
            context: The AgentContext.
            **kwargs: Keyword arguments to be passed to the tool's _execute method.

        Returns:
            The result from the tool's _execute method.
        
        Raises:
            Exception: Propagates exceptions from _execute.
        """
        tool_name = self.get_name()
        logger.info(f"Executing tool: '{tool_name}' with context for agent '{context.agent_id}'. Arguments (keys): {list(kwargs.keys())}")
        try:
            result = await self._execute(context, **kwargs)
            logger.info(f"Tool '{tool_name}' executed successfully for agent '{context.agent_id}'.")
            # Consider logging result preview if appropriate and not too verbose/sensitive.
            # logger.debug(f"Tool '{tool_name}' result preview: {str(result)[:100]}")
            return result
        except Exception as e:
            logger.error(f"Error during execution of tool '{tool_name}' for agent '{context.agent_id}': {e}", exc_info=True)
            raise  # Re-raise the exception to be handled by the caller (e.g., ToolInvocationRequestEventHandler)

    @abstractmethod
    def get_name(self) -> str:
        """
        Returns the unique name of the tool. This name is used to identify
        and call the tool.

        Returns:
            A string representing the tool's unique name.
        
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.get_name must be implemented by subclasses.")

    @abstractmethod
    def tool_usage_xml(self) -> str:
        """
        Returns an XML-formatted string describing how to use the tool.
        This is typically used to inform the LLM about the tool's capabilities
        and invocation syntax.

        Returns:
            An XML string detailing the tool's usage.
        
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.tool_usage_xml must be implemented by subclasses.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.get_name() if hasattr(self, 'get_name') and callable(self.get_name) else 'N/A'}'>"

