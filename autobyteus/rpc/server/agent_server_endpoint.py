# file: autobyteus/autobyteus/rpc/server/agent_server_endpoint.py
import asyncio
import logging
from typing import Optional, Dict, Union

from autobyteus.rpc.config import AgentServerConfig
from autobyteus.rpc.transport_type import TransportType
from autobyteus.rpc.protocol import RequestType
from autobyteus.agent.agent import Agent 
from .base_method_handler import BaseMethodHandler
from .method_handlers import DiscoverCapabilitiesHandler, InvokeMethodHandler, InitiateStreamDownloadHandler # Added InitiateStreamDownloadHandler
from .stdio_server_handler import StdioServerHandler
from .sse_server_handler import SseServerHandler

logger = logging.getLogger(__name__)

class AgentServerEndpoint:
    """
    Manages the server-side RPC endpoint.
    It can serve a single Agent or a dictionary of multiple Agents (for SSE).
    It initializes and controls transport-specific handlers.
    """

    def __init__(self, agent_or_agents: Union[Agent, Dict[str, Agent]]):
        """
        Initializes the AgentServerEndpoint.

        Args:
            agent_or_agents: Either a single Agent instance to serve, or a dictionary
                             mapping server-routable agent IDs to Agent instances
                             (primarily for multi-agent SSE hosting).
        """
        if not isinstance(agent_or_agents, (Agent, dict)):
            raise TypeError("AgentServerEndpoint requires an Agent instance or a Dict[str, Agent].")
        if isinstance(agent_or_agents, dict) and not all(isinstance(k, str) and isinstance(v, Agent) for k, v in agent_or_agents.items()):
            raise TypeError("If agent_or_agents is a dict, keys must be strings and values must be Agent instances.")

        self._served_entity: Union[Agent, Dict[str, Agent]] = agent_or_agents
        self._config: Optional[AgentServerConfig] = None
        
        # Initialize method handlers
        # These handlers are stateless and can be reused.
        # For stateful handlers, they might need to be instantiated per request or per agent context.
        self._method_handlers: Dict[Union[RequestType, str], BaseMethodHandler] = {
            RequestType.DISCOVER_CAPABILITIES: DiscoverCapabilitiesHandler(),
            RequestType.INVOKE_METHOD: InvokeMethodHandler(),
            RequestType.REQUEST_STREAM_DOWNLOAD: InitiateStreamDownloadHandler(), # Added handler for stream download
        }
        
        self._stdio_handler: Optional[StdioServerHandler] = None
        self._stdio_task: Optional[asyncio.Task] = None
        
        self._sse_handler: Optional[SseServerHandler] = None
        self._sse_server_task: Optional[asyncio.Task] = None # For the aiohttp server itself

        self._is_running: bool = False
        
        if isinstance(self._served_entity, Agent):
            logger.info(f"AgentServerEndpoint initialized for single agent '{self._served_entity.agent_id}'.")
        else: # Dict[str, Agent]
            agent_ids_served = list(self._served_entity.keys())
            logger.info(f"AgentServerEndpoint initialized to serve multiple agents: {agent_ids_served}.")


    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self, config: AgentServerConfig) -> None:
        if self._is_running:
            served_id = self._served_entity.agent_id if isinstance(self._served_entity, Agent) else "multiple agents"
            logger.warning(f"AgentServerEndpoint for '{served_id}' is already running. Ignoring start request.")
            return

        if not isinstance(config, AgentServerConfig):
            raise TypeError("AgentServerConfig instance required to start AgentServerEndpoint.")
        
        self._config = config
        served_id_log = self._served_entity.agent_id if isinstance(self._served_entity, Agent) else f"multiple agents ({list(self._served_entity.keys())})" # type: ignore
        logger.info(f"AgentServerEndpoint for '{served_id_log}' starting with config '{config.server_id}' (Transport: {config.transport_type.value}).")

        if self._config.transport_type == TransportType.STDIO:
            if not isinstance(self._served_entity, Agent):
                raise ValueError("STDIO transport currently supports serving only a single Agent instance.")
            single_agent_for_stdio: Agent = self._served_entity

            if not self._stdio_handler: # Create handler if it doesn't exist
                self._stdio_handler = StdioServerHandler(single_agent_for_stdio, self._method_handlers) 
            
            # Ensure task is not already running or is completed
            if self._stdio_task and not self._stdio_task.done():
                 logger.warning(f"Stdio task for agent '{single_agent_for_stdio.agent_id}' seems to be already running. Not restarting.")
            else:
                self._stdio_task = asyncio.create_task(
                    self._stdio_handler.listen_and_dispatch(),
                    name=f"stdio_server_endpoint_{single_agent_for_stdio.agent_id}"
                )
            logger.info(f"Stdio transport for agent '{single_agent_for_stdio.agent_id}' started via StdioServerHandler.")
        
        elif self._config.transport_type == TransportType.SSE:
            agents_for_sse: Dict[str, Agent]
            if isinstance(self._served_entity, Agent):
                agents_for_sse = {self._served_entity.agent_id: self._served_entity}
                logger.info(f"Serving single agent '{self._served_entity.agent_id}' via SSE under its own agent_id as the server key.")
            elif isinstance(self._served_entity, dict):
                agents_for_sse = self._served_entity
            else: 
                 raise ValueError("Invalid _served_entity type for SSE transport.")


            if not self._sse_handler: # Create handler if it doesn't exist
                self._sse_handler = SseServerHandler(agents_for_sse, self._method_handlers)
            
            if self._sse_server_task and not self._sse_server_task.done():
                logger.warning("SSE server task seems to be already running. Not restarting.")
            else:
                # SseServerHandler.start_server is a blocking call that runs the aiohttp server.
                # It should be run in a task that this endpoint manages.
                self._sse_server_task = asyncio.create_task(
                    self._sse_handler.start_server(config), 
                    name=f"sse_server_endpoint_manager" 
                )
            logger.info(f"SSE transport starting via SseServerHandler for agents: {list(agents_for_sse.keys())}.")

        else:
            logger.error(f"Unsupported transport type '{self._config.transport_type}' in AgentServerEndpoint.")
            self._config = None # Reset config if start fails for this reason
            raise NotImplementedError(f"Transport type '{self._config.transport_type}' not implemented.")

        self._is_running = True
        logger.info(f"AgentServerEndpoint for '{served_id_log}' started successfully.")

    async def stop(self) -> None:
        served_id_log = self._served_entity.agent_id if isinstance(self._served_entity, Agent) else f"multiple agents ({list(self._served_entity.keys())})" # type: ignore
        if not self._is_running:
            logger.warning(f"AgentServerEndpoint for '{served_id_log}' is not running. Ignoring stop request.")
            return

        logger.info(f"AgentServerEndpoint for '{served_id_log}' stopping...")

        # Stop transport-specific handlers/tasks
        if self._config and self._config.transport_type == TransportType.STDIO:
            if self._stdio_handler: # StdioServerHandler manages its own _running flag
                self._stdio_handler.stop() # Signal handler to stop listening
            if self._stdio_task and not self._stdio_task.done():
                self._stdio_task.cancel() # Cancel the listen_and_dispatch task
                try: await self._stdio_task
                except asyncio.CancelledError: logger.info(f"Stdio task for endpoint for '{served_id_log}' cancelled.")
                except Exception as e: logger.error(f"Error awaiting stdio_task during stop: {e}", exc_info=True)
            self._stdio_task = None
            # self._stdio_handler = None # Handler can be reused if started again
            logger.info(f"Stdio transport for endpoint '{served_id_log}' stopped.")

        elif self._config and self._config.transport_type == TransportType.SSE:
            if self._sse_handler: # SseServerHandler has its own stop_server method
                await self._sse_handler.stop_server() 
            if self._sse_server_task and not self._sse_server_task.done():
                # The sse_handler.stop_server() should ideally cause the task awaiting sse_handler.start_server() to complete.
                # If start_server is not designed to unblock on stop_server, cancellation might be needed.
                # Assuming start_server will handle cleanup and exit gracefully when stop_server is called.
                # If not, explicit cancellation might be required here.
                try: 
                    # Give some time for graceful shutdown initiated by stop_server()
                    await asyncio.wait_for(self._sse_server_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for SSE server task for '{served_id_log}' to complete. Cancelling.")
                    self._sse_server_task.cancel()
                    try: await self._sse_server_task
                    except asyncio.CancelledError: logger.info(f"SSE server task for endpoint '{served_id_log}' cancelled.")
                except asyncio.CancelledError: # If already cancelled by internal logic
                     logger.info(f"SSE server task for endpoint '{served_id_log}' was already cancelled.")
                except Exception as e: logger.error(f"Error awaiting sse_server_task during stop: {e}", exc_info=True)
            
            self._sse_server_task = None
            # self._sse_handler = None # Handler can be reused
            logger.info(f"SSE transport for endpoint '{served_id_log}' stopped.")

        self._is_running = False
        self._config = None # Clear current config
        logger.info(f"AgentServerEndpoint for '{served_id_log}' stopped successfully.")

