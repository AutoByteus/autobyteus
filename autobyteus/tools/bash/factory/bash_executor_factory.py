from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.bash.bash_executor import BashExecutor

class BashExecutorFactory(ToolFactory):
    def create_tool(self) -> BashExecutor:
        return BashExecutor()