# file: autobyteus/autobyteus/cli/workflow_cli.py
import asyncio
import logging
import sys
from typing import Optional

from ..agent.workflow.agentic_workflow import AgenticWorkflow
from ..agent.message.agent_input_user_message import AgentInputUserMessage
from ..agent.workflow.streaming.workflow_event_stream import WorkflowEventStream
from .workflow_cli_display import InteractiveWorkflowCLIDisplay

logger = logging.getLogger(__name__)

async def run_workflow(workflow: AgenticWorkflow, initial_prompt: Optional[str] = None):
    """Runs an interactive CLI for a multi-agent workflow."""
    if not isinstance(workflow, AgenticWorkflow):
        raise TypeError(f"Expected an AgenticWorkflow instance, got {type(workflow).__name__}")

    logger.info(f"Starting interactive CLI session for workflow '{workflow.workflow_id}'.")
    turn_complete_event = asyncio.Event()
    cli_display = InteractiveWorkflowCLIDisplay(turn_complete_event)
    streamer = WorkflowEventStream(workflow)

    async def process_workflow_events():
        try:
            async for event in streamer.all_events():
                await cli_display.handle_stream_event(event)
        except asyncio.CancelledError:
            logger.info("Workflow CLI event processing cancelled.")
        except Exception as e:
            logger.error(f"Error in workflow CLI event loop: {e}", exc_info=True)
        finally:
            turn_complete_event.set()

    event_task = asyncio.create_task(process_workflow_events())

    try:
        if not workflow.is_running:
            workflow.start()
        
        turn_complete_event.set() # Start in an idle state
        await turn_complete_event.wait()

        if initial_prompt:
            print(f"You: {initial_prompt}")
            turn_complete_event.clear()
            await workflow.post_user_message(AgentInputUserMessage(content=initial_prompt))
            await turn_complete_event.wait()
        
        while True:
            turn_complete_event.clear()
            sys.stdout.write("You: ")
            sys.stdout.flush()
            user_input = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            user_input = user_input.rstrip('\n')

            if user_input.lower().strip() in ["/quit", "/exit"]:
                break
            if not user_input.strip():
                continue

            await workflow.post_user_message(AgentInputUserMessage(content=user_input))
            await turn_complete_event.wait()

    except (KeyboardInterrupt, EOFError):
        logger.info("Exit signal received.")
    finally:
        logger.info("Shutting down workflow session...")
        if not event_task.done():
            event_task.cancel()
        
        if workflow.is_running:
            await workflow.stop()
        
        await streamer.close()
        logger.info("Workflow session finished.")
