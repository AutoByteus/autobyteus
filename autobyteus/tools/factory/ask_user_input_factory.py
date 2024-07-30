from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.ask_user_input import AskUserInput

class AskUserInputFactory(ToolFactory):
    def create_tool(self) -> AskUserInput:
        return AskUserInput()