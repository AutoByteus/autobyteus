# file: autobyteus/autobyteus/rpc/hosting.py
import asyncio
import logging
import signal
from typing import Optional, Dict, Union # Added Dict, Union

from autobyteus.agent.agent import Agent
from autobyteus.rpc.server import AgentServerEndpoint
from autobyteus.rpc.config import AgentServerConfig
from autobyteus.rpc.transport_type import TransportType

logger = logging.getLogger(__name__)

async def serve_agent_stdio(
    agent: Agent,
    stop_event: asyncio.Event,
    server_id_for_config: Optional[str] = None
) -> None:
    """
    Hosts a single Agent instance over STDIO within the current process.
    This function will run until the stop_event is set.
    The script calling this function will dedicate its sys.stdin/sys.stdout
    to RPC communication.

    Args:
        agent: The Agent instance to serve.
        stop_event: An asyncio.Event that signals when to stop the server.
        server_id_for_config: Optional string to use as server_id in the internal
                              AgentServerConfig. Defaults to f"embedded_stdio_{agent.agent_id}".
    """
    if not isinstance(agent, Agent):
        raise TypeError("agent must be an instance of autobyteus.agent.agent.Agent")
    if not isinstance(stop_event, asyncio.Event):
        raise TypeError("stop_event must be an asyncio.Event")

    actual_server_id = server_id_for_config or f"embedded_stdio_{agent.agent_id}"
    
    stdio_config = AgentServerConfig(
        server_id=actual_server_id,
        transport_type=TransportType.STDIO,
        stdio_command=["in-process-stdio-server"] 
    )
    logger.info(f"Configuring in-process STDIO server for agent '{agent.agent_id}' with config_id '{actual_server_id}'.")

    server_endpoint = AgentServerEndpoint(agent) # Pass single agent

    try:
        if not agent.is_running:
            logger.info(f"Starting agent '{agent.agent_id}' for STDIO hosting...")
            agent.start() 

        logger.info(f"Starting STDIO server endpoint for agent '{agent.agent_id}'...")
        await server_endpoint.start(stdio_config)
        
        logger.info(f"Agent '{agent.agent_id}' now being served via STDIO. Waiting for stop signal...")
        await stop_event.wait()
        logger.info(f"Stop signal received for STDIO server of agent '{agent.agent_id}'.")

    except Exception as e:
        logger.error(f"Error during STDIO hosting for agent '{agent.agent_id}': {e}", exc_info=True)
    finally:
        logger.info(f"Shutting down STDIO server for agent '{agent.agent_id}'...")
        if server_endpoint.is_running:
            await server_endpoint.stop()
        
        if agent.is_running: 
            logger.info(f"Stopping agent '{agent.agent_id}' after STDIO hosting...")
            await agent.stop()
        logger.info(f"STDIO hosting for agent '{agent.agent_id}' has shut down.")


async def serve_single_agent_http_sse(
    agent: Agent,
    host: str,
    port: int,
    stop_event: asyncio.Event,
    server_id_prefix: str = "embedded_http_single",
    request_endpoint: str = "/rpc",
    events_endpoint_base: str = "/events" # Base path for events
) -> None:
    """
    Hosts a single Agent instance over HTTP/SSE within the current process.
    The agent will be accessible using its own agent_id as the key on the server
    (e.g., for SSE events: /events/{agent.agent_id}).

    Args:
        agent: The Agent instance to serve.
        host: The hostname or IP address to bind the HTTP server to.
        port: The port number to bind the HTTP server to.
        stop_event: An asyncio.Event that signals when to stop the server.
        server_id_prefix: Prefix for the server_id in the internal AgentServerConfig.
        request_endpoint: The URL path for RPC requests.
        events_endpoint_base: The base URL path for SSE event streams (agent_id will be appended).
    """
    # This function now essentially calls serve_multiple_agents_http_sse
    # The agent's own ID will be used as the key for routing on the server.
    agents_to_serve = {agent.agent_id: agent}
    await serve_multiple_agents_http_sse(
        agents=agents_to_serve,
        host=host,
        port=port,
        stop_event=stop_event,
        server_id_prefix=server_id_prefix,
        request_endpoint=request_endpoint,
        events_endpoint_base=events_endpoint_base
    )


async def serve_multiple_agents_http_sse(
    agents: Dict[str, Agent], # Key: server-routable ID, Value: Agent instance
    host: str,
    port: int,
    stop_event: asyncio.Event,
    server_id_prefix: str = "embedded_http_multi",
    request_endpoint: str = "/rpc", # Single RPC endpoint for the gateway
    events_endpoint_base: str = "/events" # Base for /events/{agent_id_on_server}
) -> None:
    """
    Hosts multiple Agent instances over a single HTTP/SSE server within the current process.
    This function will run until the stop_event is set.

    Args:
        agents: A dictionary where keys are server-routable string IDs for each agent,
                and values are the Agent instances to serve.
        host: The hostname or IP address to bind the HTTP server to.
        port: The port number to bind the HTTP server to.
        stop_event: An asyncio.Event that signals when to stop the server.
        server_id_prefix: Prefix for the server_id in the internal AgentServerConfig for the gateway.
        request_endpoint: The URL path for all RPC requests (target_agent_id must be in payload).
        events_endpoint_base: The base URL path for SSE event streams. Clients subscribe to
                              {events_endpoint_base}/{server_routable_agent_id}.
    """
    if not isinstance(agents, dict) or not agents:
        raise TypeError("agents must be a non-empty dictionary of [str, Agent] instances.")
    if not all(isinstance(k, str) and isinstance(v, Agent) for k, v in agents.items()):
        raise TypeError("agents dictionary keys must be strings and values must be Agent instances.")
    if not isinstance(stop_event, asyncio.Event):
        raise TypeError("stop_event must be an asyncio.Event")

    # server_id for the gateway server config
    gateway_server_id = f"{server_id_prefix}_gateway" 
    
    sse_config = AgentServerConfig(
        server_id=gateway_server_id,
        transport_type=TransportType.SSE,
        sse_base_url=f"http://{host}:{port}", # type: ignore
        sse_request_endpoint=request_endpoint,
        sse_events_endpoint=events_endpoint_base # SseServerHandler will append /{agent_id_on_server}
    )
    routable_agent_ids = list(agents.keys())
    logger.info(f"Configuring in-process HTTP/SSE gateway server at {sse_config.sse_base_url} "
                f"(config_id: '{gateway_server_id}') to serve agents: {routable_agent_ids}.")

    server_endpoint = AgentServerEndpoint(agents) # Pass the dictionary of agents

    try:
        for agent_id_on_server, agent_instance in agents.items():
            if not agent_instance.is_running:
                logger.info(f"Starting agent '{agent_instance.agent_id}' (server key: '{agent_id_on_server}') for HTTP/SSE gateway hosting...")
                agent_instance.start()

        logger.info(f"Starting HTTP/SSE gateway server endpoint for agents: {routable_agent_ids}...")
        await server_endpoint.start(sse_config)
        
        logger.info(f"Multi-agent gateway now being served via HTTP/SSE on http://{host}:{port}. Waiting for stop signal...")
        await stop_event.wait()
        logger.info(f"Stop signal received for multi-agent HTTP/SSE gateway server.")

    except Exception as e:
        logger.error(f"Error during multi-agent HTTP/SSE hosting: {e}", exc_info=True)
    finally:
        logger.info(f"Shutting down multi-agent HTTP/SSE gateway server...")
        if server_endpoint.is_running:
            await server_endpoint.stop()
        
        for agent_id_on_server, agent_instance in agents.items():
            if agent_instance.is_running:
                logger.info(f"Stopping agent '{agent_instance.agent_id}' (server key: '{agent_id_on_server}')...")
                await agent_instance.stop()
        logger.info(f"Multi-agent HTTP/SSE hosting has shut down.")


# Renamed old serve_agent_http_sse to serve_single_agent_http_sse
# Kept the old signature for backward compatibility if any tests used it,
# but it now delegates to the multi-agent version.
async def serve_agent_http_sse(
    agent: Agent,
    host: str,
    port: int,
    stop_event: asyncio.Event,
    server_id_prefix: str = "embedded_http", # Note: prefix change if desired
    request_endpoint: str = "/rpc",
    events_endpoint_base: str = "/events" 
) -> None:
     await serve_single_agent_http_sse(
         agent, host, port, stop_event, server_id_prefix, request_endpoint, events_endpoint_base
     )


if __name__ == "__main__": # pragma: no cover
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    from autobyteus.agent.registry.agent_definition import AgentDefinition
    from autobyteus.agent.registry.agent_registry import default_agent_registry, default_definition_registry
    from autobyteus.llm.models import LLMModel
    try: import autobyteus.agent.input_processor 
    except ImportError: print("Warning: input_processor module not found.", file=sys.stderr)

    def create_example_agent(name: str, role: str) -> Optional[Agent]:
        agent_def = default_definition_registry.get(name, role)
        if not agent_def:
            try:
                agent_def = AgentDefinition(name=name, role=role, description=f"{name} agent",
                                            system_prompt=f"You are {name}.", tool_names=[],
                                            input_processor_names=["PassthroughInputProcessor"])
            except Exception as e_def:
                logger.error(f"Failed to create def for {name}: {e_def}"); return None
        
        try: chosen_llm_model = next(iter(LLMModel)) if LLMModel else None
        except StopIteration: chosen_llm_model = None
        if not chosen_llm_model:
            class MockLLMModel(str, Enum): DUMMY = "dummy_model" # type: ignore
            LLMModel = MockLLMModel # type: ignore
            chosen_llm_model = LLMModel.DUMMY
        
        if chosen_llm_model:
            try: return default_agent_registry.create_agent(definition=agent_def, llm_model=chosen_llm_model)
            except Exception as e_create: logger.error(f"Failed to create agent {name}: {e_create}", exc_info=True)
        return None

    agent1 = create_example_agent("AgentAlpha", "analyzer")
    agent2 = create_example_agent("AgentBeta", "writer")

    if agent1 and agent2:
        agents_for_server = {
            "alpha": agent1, # Routable ID "alpha" maps to AgentAlpha
            "beta": agent2   # Routable ID "beta" maps to AgentBeta
        }
        # Example: Run the multi-agent SSE server
        asyncio.run(serve_multiple_agents_http_sse(agents_for_server, "127.0.0.1", 8888, asyncio.Event()))
        # To test, connect to http://127.0.0.1:8888/events/alpha and /events/beta for SSE
        # Send POST to http://127.0.0.1:8888/rpc with {"target_agent_id": "alpha", ...}
    else:
        logger.error("Could not create example agents for multi-agent hosting demo.")

