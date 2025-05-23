import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.tools import tool # Main @tool decorator

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="AskUserInput") # Explicit name matching the old class name
async def ask_user_input(context: 'AgentContext', request: str) -> str: # Function name can be ask_user_input
    """
    Requests input from the user based on a given prompt and returns the user's textual response.
    'request' is the prompt or question to present to the user.
    """
    logger.info(f"Functional AskUserInput tool (agent {context.agent_id}) requesting user input: {request}")

    try:
        loop = asyncio.get_event_loop()
        user_input_str = await loop.run_in_executor(
            None, 
            lambda: input(f"LLM Agent ({context.agent_id}): {request}\nUser: ")
        )
        
        logger.info(f"User input received for agent {context.agent_id}: '{user_input_str[:50]}...'")
        return user_input_str

    except KeyboardInterrupt:
        logger.warning(f"User interrupted input process for agent {context.agent_id}.")
        return "[Input process interrupted by user]"
    except EOFError:
        logger.warning(f"EOF error during input for agent {context.agent_id}.")
        return "[EOF error occurred during input]"
    except Exception as e:
        error_message = f"An error occurred while getting user input: {str(e)}"
        logger.error(error_message, exc_info=True)
        return f"[Error getting user input: {error_message}]"
