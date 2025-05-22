# File: autobyteus/tools/ask_user_input.py

import logging
from typing import TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class AskUserInput(BaseTool):
    """
    A tool that allows a large language model to request input from the user.
    """

    def __init__(self):
        super().__init__()

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the AskUserInput tool.

        Returns:
            str: An XML description of how to use the AskUserInput tool.
        """
        return '''AskUserInput: Requests input from the user based on a given context or prompt. 
    <command name="AskUserInput">
    <arg name="request">[Your request here]</arg>
    </command>

    Examples:
    1. When needing to request user for search input:
    <command name="AskUserInput">
    <arg name="request">What would you like to search for?</arg>
    </command>

    2. When needing to request user for form input:
    <command name="AskUserInput">
    <arg name="request">Please enter your full name:</arg>
    </command>

    3. When needing to request user for a choice:
    <command name="AskUserInput">
    <arg name="request">Select an option (1, 2, or 3):</arg>
    </command>
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Present the LLM's request to the user, capture their input, and return it.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Keyword arguments containing the LLM's request.
                      'request': The request or prompt from the LLM to present to the user.

        Returns:
            str: The user's input in response to the LLM's request.

        Raises:
            ValueError: If the 'request' keyword argument is not specified.
        """
        request_prompt = kwargs.get('request') # Renamed variable to avoid conflict with 'request' module

        if not request_prompt:
            raise ValueError("The 'request' keyword argument must be specified.")

        logger.info(f"Agent '{context.agent_id}' (LLM) requesting user input: {request_prompt}")

        try:
            # This is a blocking input call. In a real async application,
            # this would need to be handled differently (e.g., via an external event,
            # or asyncio.to_thread if this tool is expected to block the agent's event loop).
            # For simplicity as per original code, using direct input().
            print(f"LLM (Agent {context.agent_id}): {request_prompt}")
            user_input = input(f"User (replying to Agent {context.agent_id}): ") # Indicate which agent is asking

            logger.info(f"Agent '{context.agent_id}': User input received: '{user_input[:50]}...'")
            return user_input

        except KeyboardInterrupt:
            logger.warning(f"Agent '{context.agent_id}': User interrupted the input process.")
            return "[Input process interrupted by user]"
        except EOFError: # pragma: no cover
            logger.warning(f"Agent '{context.agent_id}': EOF error occurred during input.")
            return "[EOF error occurred]"
        except Exception as e: # pragma: no cover
            error_message = f"An error occurred while getting user input for agent '{context.agent_id}': {str(e)}"
            logger.error(error_message, exc_info=True)
            return f"[Error: {error_message}]"
