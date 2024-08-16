# File: autobyteus/tools/ask_user_input.py

import logging
from autobyteus.tools.base_tool import BaseTool

class AskUserInput(BaseTool):
    """
    A tool that allows a large language model to request input from the user.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def tool_usage(self):
        """
        Return a string describing the usage of the AskUserInput tool.
        """
        return '''AskUserInput: Requests input from the user based on LLM's prompt. 
        Usage: <<<AskUserInput(request="[Your request here]")>>>
        
        Examples:
        1. When needing to request user for search input:
           <<<AskUserInput(request="What would you like to search for?")>>>
        
        2. When needing to request user for form input:
           <<<AskUserInput(request="Please enter your full name:")>>>
        
        3. When needing to request user for a choice:
           <<<AskUserInput(request="Select an option (1, 2, or 3):")>>>
        '''

    def tool_usage_xml(self):
        return '''AskUserInput: Requests input from the user based on a given context or prompt. 
    <command name="AskUserInput"
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

    async def _execute(self, **kwargs):
        """
        Present the LLM's request to the user, capture their input, and return it.

        Args:
            **kwargs: Keyword arguments containing the LLM's request.
                      'request': The request or prompt from the LLM to present to the user.

        Returns:
            str: The user's input in response to the LLM's request.

        Raises:
            ValueError: If the 'request' keyword argument is not specified.
        """
        request = kwargs.get('request')

        if not request:
            raise ValueError("The 'request' keyword argument must be specified.")

        self.logger.info(f"LLM requesting user input: {request}")

        try:
            print(f"LLM: {request}")
            user_input = input("User: ")

            self.logger.info("User input received.")
            return user_input

        except KeyboardInterrupt:
            self.logger.warning("User interrupted the input process.")
            return "[Input process interrupted by user]"
        except EOFError:
            self.logger.warning("EOF error occurred during input.")
            return "[EOF error occurred]"
        except Exception as e:
            error_message = f"An error occurred while getting user input: {str(e)}"
            self.logger.error(error_message)
            return f"[Error: {error_message}]"