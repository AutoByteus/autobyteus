# file: autobyteus/autobyteus/mcp/tool.py
import logging
from typing import Any, Optional, TYPE_CHECKING, Dict, Set
import asyncio

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from .connection_manager import McpConnectionManager 

logger = logging.getLogger(__name__)

class GenericMcpTool(BaseTool):
    """
    A generic tool wrapper for executing tools on a remote MCP server.
    This tool is instantiated by a custom factory specific to a discovered
    remote MCP tool. It overrides the base class's schema methods
    to provide instance-specific details for execution-time validation.
    """

    def __init__(self,
                 mcp_server_id: str,
                 mcp_remote_tool_name: str,
                 mcp_connection_manager: 'McpConnectionManager',
                 name: str, 
                 description: str,
                 argument_schema: ParameterSchema):
        """
        Initializes the GenericMcpTool instance.
        """
        super().__init__() 
        
        self._mcp_server_id = mcp_server_id
        self._mcp_remote_tool_name = mcp_remote_tool_name
        self._mcp_connection_manager = mcp_connection_manager
        
        self._instance_name = name
        self._instance_description = description
        self._instance_argument_schema = argument_schema
        
        # Override the base class's schema-related methods with instance-specific
        # versions. This is crucial for the BaseTool.execute method to correctly
        # validate arguments before calling our _execute method.
        self.get_name = self.get_instance_name
        self.get_description = self.get_instance_description
        self.get_argument_schema = self.get_instance_argument_schema
        
        logger.info(f"GenericMcpTool instance created for remote tool '{mcp_remote_tool_name}' on server '{self._mcp_server_id}'. "
                    f"Registered in AutoByteUs as '{self._instance_name}'.")

    # --- Getters for instance-specific data ---

    def get_instance_name(self) -> str:
        return self._instance_name

    def get_instance_description(self) -> str:
        return self._instance_description

    def get_instance_argument_schema(self) -> ParameterSchema:
        return self._instance_argument_schema

    # --- Base class methods that are NOT overridden at instance level ---

    @classmethod
    def get_name(cls) -> str:
        return "GenericMcpTool" 

    @classmethod
    def get_description(cls) -> str:
        return "A generic wrapper for executing tools on a remote MCP server. Specifics are instance-based."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return None 

    async def _execute(self, context: 'AgentContext', **kwargs: Any) -> Any:
        """
        Executes the remote MCP tool call.
        """
        # self.get_name() will now call the instance's method and return the specific name
        tool_name_for_log = self.get_instance_name()
        logger.info(f"GenericMcpTool '{tool_name_for_log}': Executing remote tool '{self._mcp_remote_tool_name}' "
                    f"on server '{self._mcp_server_id}' with args: {kwargs}")
        
        if not self._mcp_connection_manager: 
             logger.error(f"GenericMcpTool '{tool_name_for_log}': McpConnectionManager is not set. Cannot execute.")
             raise RuntimeError("McpConnectionManager not available in GenericMcpTool instance.")

        try:
            session = await self._mcp_connection_manager.get_session(self._mcp_server_id)
        except Exception as e:
            logger.error(f"GenericMcpTool '{tool_name_for_log}': Failed to get MCP session for server '{self._mcp_server_id}': {e}", exc_info=True)
            raise RuntimeError(f"Failed to acquire MCP session for server '{self._mcp_server_id}': {e}") from e

        # This block is an explicit way to prevent a deadlock.
        # The mcp.ClientSession runs a background task to read server responses. If the
        # current task (this _execute method) blocks the event loop by awaiting
        # `session.call_tool` directly, the background reader may never get a chance
        # to run and process the response, causing a deadlock.
        #
        # To solve this, we explicitly create a task for the tool call and use
        # `asyncio.wait` to yield control to the event loop, giving the background
        # reader a chance to run.
        tool_call_task = asyncio.create_task(session.call_tool(self._mcp_remote_tool_name, kwargs))
        pending: Set[asyncio.Task] = {tool_call_task}

        try:
            while pending:
                # The waiter task ensures we yield control at least once.
                waiter_task = asyncio.create_task(asyncio.sleep(0.01))
                done, pending = await asyncio.wait(
                    pending.union({waiter_task}), 
                    return_when=asyncio.FIRST_COMPLETED
                )

                # If the waiter task finished, we just loop again to check the tool call task.
                # If the tool call finished, the loop will exit.
                if waiter_task in done:
                    pending.discard(waiter_task) # No longer need to wait on the waiter
            
            # At this point, tool_call_task is in the 'done' set.
            result = await tool_call_task
            
            logger.info(f"GenericMcpTool '{tool_name_for_log}': Remote tool '{self._mcp_remote_tool_name}' executed successfully. Result preview: {str(result)[:100]}...")
            return result
        except Exception as e:
            logger.error(f"GenericMcpTool '{tool_name_for_log}': Error calling remote tool '{self._mcp_remote_tool_name}' on server '{self._mcp_server_id}': {e}", exc_info=True)
            # Ensure the task is cancelled if an error occurs during waiting.
            if not tool_call_task.done():
                tool_call_task.cancel()
            raise RuntimeError(f"Error calling remote MCP tool '{self._mcp_remote_tool_name}': {e}") from e
