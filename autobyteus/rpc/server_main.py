# file: autobyteus/autobyteus/rpc/server_main.py
import asyncio
import logging
import argparse
import signal
import sys 
from typing import Optional

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.registry.agent_registry import default_definition_registry, default_agent_registry
from autobyteus.agent.agent import Agent 
from autobyteus.llm.models import LLMModel 

from autobyteus.rpc.config import AgentServerConfig, default_agent_server_registry
from autobyteus.rpc.server import AgentServerEndpoint
from autobyteus.rpc.transport_type import TransportType

try:
    from autobyteus.agent.input_processor import PassthroughInputProcessor
except ImportError:
    print("WARNING: PassthroughInputProcessor not found, EchoAgentDefinition in server_main might fail if used.", file=sys.stderr)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - [%(process)d] - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


ECHO_AGENT_DEF: Optional[AgentDefinition] = None
try:
    if not default_definition_registry.get("EchoAgent", "echo_responder"):
        ECHO_AGENT_DEF = AgentDefinition(
            name="EchoAgent",
            role="echo_responder",
            description="A simple agent that echoes back user messages.",
            system_prompt="You are an echo agent. Repeat the user's message precisely.",
            tool_names=[], 
            input_processor_names=["PassthroughInputProcessor"], # Assumes PassthroughInputProcessor is registered
            llm_response_processor_names=[] 
        )
        logger.info(f"Example AgentDefinition '{ECHO_AGENT_DEF.name}' created and auto-registered for server_main.")
    else:
        ECHO_AGENT_DEF = default_definition_registry.get("EchoAgent", "echo_responder")
        logger.info(f"Example AgentDefinition 'EchoAgent' already registered. Using existing one for server_main.")
except Exception as e:
    logger.error(f"Could not create/retrieve example EchoAgentDefinition: {e}. server_main might fail if it's requested.")


shutdown_event = asyncio.Event()
agent_global: Optional[Agent] = None 
server_endpoint_global: Optional[AgentServerEndpoint] = None

async def main():
    global agent_global, server_endpoint_global

    parser = argparse.ArgumentParser(description="AutoByteUs Agent RPC Server") 
    parser.add_argument("--agent-def-name", type=str, required=True, help="Name of the AgentDefinition.")
    parser.add_argument("--agent-def-role", type=str, required=True, help="Role of the AgentDefinition.")
    parser.add_argument("--llm-model-name", type=str, required=True, help="Name of the LLMModel (e.g., 'GPT_4o_API'). This is the string name for the model, not the enum member itself.")
    parser.add_argument("--server-config-id", type=str, required=True, help="ID of the AgentServerConfig.")
    
    args = parser.parse_args()
    logger.info(f"server_main starting with args: {args}")

    agent_definition = default_definition_registry.get(args.agent_def_name, args.agent_def_role)
    if not agent_definition:
        logger.error(f"AgentDefinition not found for name='{args.agent_def_name}', role='{args.agent_def_role}'.")
        sys.exit(1)

    # The llm_model_name from args is already a string, which is what create_agent now expects.
    # We still need to validate if it's a known model name for robustness,
    # though create_agent (via AgentFactory -> AgentConfig) will also do this.
    try:
        LLMModel[args.llm_model_name.upper()] # Validate if the name maps to a known LLMModel enum member
    except KeyError:
        logger.error(f"LLMModel name '{args.llm_model_name}' provided via --llm-model-name is not a recognized LLMModel. Available: {[m.name for m in LLMModel]}")
        sys.exit(1)

    server_config = default_agent_server_registry.get_config(args.server_config_id)
    if not server_config:
        logger.error(f"AgentServerConfig not found for server_config_id='{args.server_config_id}'.")
        sys.exit(1)
    
    try:
        # UPDATED: Pass llm_model_name directly as a string.
        # AgentRegistry.create_agent -> AgentFactory.create_agent_runtime -> AgentFactory.create_agent_context
        # -> AgentConfig now takes llm_model_name: str.
        agent = default_agent_registry.create_agent(
            definition=agent_definition,
            llm_model_name=args.llm_model_name # Pass the string name
            # custom_llm_config, custom_tool_config, etc., can be added here if needed
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
        await server_endpoint.start(server_config) 

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
    # Ensure input processors are available if EchoAgentDefinition needs them
    # This try-except is more for robustness during development/examples.
    try:
        # This import ensures that processors like PassthroughInputProcessor are registered
        # if EchoAgentDefinition (or others used by server_main) depends on them.
        from autobyteus.agent import input_processor # type: ignore
    except ImportError as e_proc:
        logger.warning(f"Could not import autobyteus.agent.input_processor: {e_proc}. "
                       "Make sure custom input processors are correctly installed and registered if used by agent definitions.")


    # Example STDIO server config (remains for testing server_main directly)
    stdio_cfg_id = "default_stdio_server_cfg"
    if not default_agent_server_registry.get_config(stdio_cfg_id):
        example_stdio_cfg = AgentServerConfig(
            server_id=stdio_cfg_id,
            transport_type=TransportType.STDIO,
            # stdio_command is usually for launching this script itself as a subprocess.
            # For direct execution of server_main.py, this specific command isn't directly used
            # but a valid config is needed if --server-config-id=default_stdio_server_cfg is passed.
            stdio_command=["python", "-m", "autobyteus.rpc.server_main",
                           "--agent-def-name", "EchoAgent", 
                           "--agent-def-role", "echo_responder",
                           "--llm-model-name", "GPT_4O_API", # Example model name
                           "--server-config-id", stdio_cfg_id
                          ] 
        )
        default_agent_server_registry.register_config(example_stdio_cfg)
        logger.info(f"Registered example STDIOServerConfig '{stdio_cfg_id}'.")

    # Example SSE server config
    sse_cfg_id = "default_sse_server_cfg"
    if not default_agent_server_registry.get_config(sse_cfg_id):
        example_sse_cfg = AgentServerConfig(
            server_id=sse_cfg_id, # This ID is for the server config itself
            transport_type=TransportType.SSE,
            sse_base_url="http://localhost:8765", 
            sse_request_endpoint="/invoke_rpc", # Changed from /rpc to avoid clash with potential future global /rpc
            sse_events_endpoint="/agent_events" # Changed from /events
        )
        default_agent_server_registry.register_config(example_sse_cfg)
        logger.info(f"Registered example SseServerConfig '{sse_cfg_id}'.")

    loop = asyncio.get_event_loop()
    for sig_name_str in ('SIGINT', 'SIGTERM'):
        sig_enum_member = getattr(signal, sig_name_str, None)
        if sig_enum_member:
            try:
                loop.add_signal_handler(sig_enum_member, lambda s=sig_name_str: asyncio.create_task(initiate_shutdown_from_signal()))
            except (ValueError, RuntimeError, NotImplementedError) as e: # Might fail on Windows for SIGTERM
                 logger.warning(f"Could not set signal handler for {sig_name_str} on this platform: {e}.")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main. Shutting down.")
        if not shutdown_event.is_set(): 
            if loop.is_running():
                asyncio.ensure_future(initiate_shutdown_from_signal(), loop=loop)
            else: # Should not happen if loop was running
                loop.run_until_complete(initiate_shutdown_from_signal())
    finally:
        logger.info("Asyncio loop in server_main is finalizing.")

