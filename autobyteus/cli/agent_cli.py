import asyncio
import logging
import sys
from typing import Optional

from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from .cli_display import InteractiveCLIDisplay

logger = logging.getLogger(__name__) 

async def run(agent: Agent, show_tool_logs: bool = True, show_token_usage: bool = False, initial_prompt: Optional[str] = None):
    """
    Runs an interactive command-line interface for a single agent.

    This function orchestrates the agent's lifecycle, user input, and event streaming
    for an interactive session.

    Args:
        agent: The agent instance to run.
        show_tool_logs: If True, displays detailed logs from tool interactions.
        show_token_usage: If True, displays token usage information after each LLM call.
        initial_prompt: An optional initial prompt to send to the agent automatically.
    """
    if not isinstance(agent, Agent):
        raise TypeError(f"Expected an Agent instance, got {type(agent).__name__}")

    logger.info(f"Starting interactive CLI session for agent '{agent.agent_id}'.")
    agent_turn_complete_event = asyncio.Event()
    cli_display = InteractiveCLIDisplay(agent_turn_complete_event, show_tool_logs, show_token_usage)
    streamer = AgentEventStream(agent)

    async def process_agent_events():
        """Task to continuously process and display events from the agent."""
        try:
            async for event in streamer.all_events():
                await cli_display.handle_stream_event(event)
        except asyncio.CancelledError:
            logger.info("CLI event processing task cancelled.")
        except Exception as e:
            logger.error(f"Error in CLI event processing loop: {e}", exc_info=True)
        finally:
            logger.debug("CLI event processing task finished.")
            agent_turn_complete_event.set() # Ensure main loop isn't stuck

    event_task = asyncio.create_task(process_agent_events())

    try:
        if not agent.is_running:
            agent.start()
        
        logger.debug("Waiting for agent to initialize and become idle...")
        try:
            await asyncio.wait_for(agent_turn_complete_event.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(f"Agent did not become idle within 30 seconds. Exiting.")
            return

        if initial_prompt:
            logger.info(f"Initial prompt provided: '{initial_prompt}'")
            print(f"You: {initial_prompt}")
            agent_turn_complete_event.clear()
            cli_display.reset_turn_state()
            await agent.post_user_message(AgentInputUserMessage(content=initial_prompt))
            await agent_turn_complete_event.wait()
        
        # Main input loop
        while True:
            agent_turn_complete_event.clear()

            if cli_display.pending_approval_data:
                approval_input = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                approval_input = approval_input.strip().lower()
                
                approval_data = cli_display.pending_approval_data
                cli_display.pending_approval_data = None
                
                is_approved = approval_input in ["y", "yes"]
                reason = "User approved via CLI" if is_approved else "User denied via CLI"
                
                await agent.post_tool_execution_approval(approval_data.invocation_id, is_approved, reason)

            else:
                sys.stdout.write("You: ")
                sys.stdout.flush()
                user_input = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                user_input = user_input.rstrip('\n')

                if user_input.lower().strip() in ["/quit", "/exit"]:
                    break
                if not user_input.strip():
                    continue

                cli_display.reset_turn_state()
                await agent.post_user_message(AgentInputUserMessage(content=user_input))

            await agent_turn_complete_event.wait()

    except (KeyboardInterrupt, EOFError):
        logger.info("Exit signal received.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the CLI main loop: {e}", exc_info=True)
    finally:
        logger.info("Shutting down interactive session...")
        if not event_task.done():
            event_task.cancel()
            try:
                await event_task
            except asyncio.CancelledError:
                pass
        
        if agent.is_running:
            await agent.stop()
        
        await streamer.close()
        logger.info("Interactive session finished.")
