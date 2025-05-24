# file: autobyteus/autobyteus/rpc/server_main.py
import asyncio
import logging
import argparse
import signal
import sys 

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.registry.agent_registry import default_definition_registry_instance, default_agent_registry
from autobyteus.agent.agent import Agent 
from autobyteus.llm.models import LLMModel 

from autobyteus.rpc.config import AgentServerConfig, default_agent_server_registry
from autobyteus.rpc.server import AgentServerEndpoint
from autobyteus.rpc.transport_type import TransportType

try:
    from autobyteus.agent.input_processor import PassthroughInputProcessor
except ImportError:
    # logging not configured yet at top level import time, print for early diagnostics
    print("WARNING: PassthroughInputProcessor not found, EchoAgentDefinition in server_main might fail if used.", file=sys.stderr)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - [%(process)d] - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


ECHO_AGENT_DEF: Optional[AgentDefinition] = None
try:
    if not default_definition_registry_instance.get("EchoAgent", "echo_responder"):
        ECHO_AGENT_DEF = AgentDefinition(
            name="EchoAgent",
            role="echo_responder",
            description="A simple agent that echoes back user messages.",
            system_prompt="You are an echo agent. Repeat the user's message precisely.",
            tool_names=[], 
            input_processor_names=["PassthroughInputProcessor"],
            llm_response_processor_names=[] 
        )
        logger.info(f"Example AgentDefinition '{ECHO_AGENT_DEF.name}' created and auto-registered for server_main.")
    else:
        ECHO_AGENT_DEF = default_definition_registry_instance.get("EchoAgent", "echo_responder")
        logger.info(f"Example AgentDefinition 'EchoAgent' already registered. Using existing one for server_main.")
except Exception as e:
    logger.error(f"Could not create/retrieve example EchoAgentDefinition: {e}. server_main might fail if it's requested.")


shutdown_event = asyncio.Event()
agent_global: Optional[Agent] = None 
server_endpoint_global: Optional[AgentServerEndpoint] = None

async def main():
    global agent_global, server_endpoint_global

    parser = argparse.ArgumentParser(description="AutoByteUs Agent RPC Server") # Title updated
    parser.add_argument("--agent-def-name", type=str, required=True, help="Name of the AgentDefinition.")
    parser.add_argument("--agent-def-role", type=str, required=True, help="Role of the AgentDefinition.")
    parser.add_argument("--llm-model-name", type=str, required=True, help="Name of the LLMModel (e.g., 'OPENAI_GPT35_TURBO').")
    parser.add_argument("--server-config-id", type=str, required=True, help="ID of the AgentServerConfig.")
    
    args = parser.parse_args()
    logger.info(f"server_main starting with args: {args}")

    agent_definition = default_definition_registry_instance.get(args.agent_def_name, args.agent_def_role)
    if not agent_definition:
        logger.error(f"AgentDefinition not found for name='{args.agent_def_name}', role='{args.agent_def_role}'.")
        sys.exit(1)

    try:
        llm_model_enum_member = LLMModel[args.llm_model_name.upper()]
    except KeyError:
        logger.error(f"LLMModel '{args.llm_model_name}' not found. Available: {[m.name for m in LLMModel]}")
        sys.exit(1)

    server_config = default_agent_server_registry.get_config(args.server_config_id)
    if not server_config:
        logger.error(f"AgentServerConfig not found for server_config_id='{args.server_config_id}'.")
        sys.exit(1)
    
    # Transport type check moved to AgentServerEndpoint or specific handlers.
    # server_main can now launch either stdio or sse based on config.

    try:
        agent = default_agent_registry.create_agent(
            definition=agent_definition,
            llm_model=llm_model_enum_member
        )
        agent_global = agent
    except Exception as e:
        logger.error(f"Failed to create Agent instance: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info(f"Agent instance created with agent_id '{agent.agent_id}'.")

    server_endpoint = AgentServerEndpoint(agent) 
    server_endpoint_global = server_endpoint
    logger.info(f"AgentServerEndpoint instantiated for agent '{agent.agent_id}'.")

    try:
        logger.info(f"Starting Agent '{agent.agent_id}' (runtime execution loop)...")
        agent.start()
        
        logger.info(f"Starting AgentServerEndpoint for agent '{agent.agent_id}' with config '{server_config.server_id}' (Transport: {server_config.transport_type.value})...")
        await server_endpoint.start(server_config) # This will block if SSE server runs in foreground, or manage task if stdio

        logger.info(f"Agent '{agent.agent_id}' is now hosted and listening via RPC ({server_config.transport_type.value}).")
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Error during server startup or main execution: {e}", exc_info=True)
    finally:
        logger.info("server_main performing final shutdown...")
        if server_endpoint_global and server_endpoint_global.is_running:
            logger.info("Stopping AgentServerEndpoint...")
            await server_endpoint_global.stop()
        
        if agent_global and agent_global.is_running: 
            logger.info(f"Stopping Agent '{agent_global.agent_id}'...")
            await agent_global.stop()
        
        logger.info("server_main has shut down.")

async def initiate_shutdown_from_signal():
    logger.debug("Initiating shutdown via signal...")
    shutdown_event.set()

if __name__ == "__main__":
    try:
        import autobyteus.agent.input_processor 
    except ImportError as e_proc:
        logger.warning(f"Could not import autobyteus.agent.input_processor: {e_proc}. Some agent definitions might fail.")

    # Example STDIO server config
    stdio_cfg_id = "default_stdio_server_cfg"
    if not default_agent_server_registry.get_config(stdio_cfg_id):
        example_stdio_cfg = AgentServerConfig(
            server_id=stdio_cfg_id,
            transport_type=TransportType.STDIO,
            stdio_command=["python", "-m", "autobyteus.rpc.server_main"] 
        )
        default_agent_server_registry.register_config(example_stdio_cfg)
        logger.info(f"Registered example '{stdio_cfg_id}'.")

    # Example SSE server config
    sse_cfg_id = "default_sse_server_cfg"
    if not default_agent_server_registry.get_config(sse_cfg_id):
        example_sse_cfg = AgentServerConfig(
            server_id=sse_cfg_id,
            transport_type=TransportType.SSE,
            sse_base_url="http://localhost:8765", # Example port
            sse_request_endpoint="/rpc",
            sse_events_endpoint="/events"
        )
        default_agent_server_registry.register_config(example_sse_cfg)
        logger.info(f"Registered example '{sse_cfg_id}'.")

    loop = asyncio.get_event_loop()
    for sig_name_str in ('SIGINT', 'SIGTERM'):
        sig_enum_member = getattr(signal, sig_name_str, None)
        if sig_enum_member:
            try:
                loop.add_signal_handler(sig_enum_member, lambda s=sig_name_str: asyncio.create_task(initiate_shutdown_from_signal()))
            except (ValueError, RuntimeError, NotImplementedError) as e:
                 logger.warning(f"Could not set signal handler for {sig_name_str}: {e}.")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main loop. Shutting down.")
        if not shutdown_event.is_set(): # Check if already initiated by signal handler
            # Ensure running in the loop if not already
            if loop.is_running():
                asyncio.ensure_future(initiate_shutdown_from_signal(), loop=loop)
            else:
                loop.run_until_complete(initiate_shutdown_from_signal())

    finally:
        logger.info("Asyncio loop tasks are being finalized.")
