# file: autobyteus/tools/factory/tool_factory.py
from abc import ABC, abstractmethod
from autobyteus.tools.base_tool import BaseTool

class ToolFactory(ABC):
    @abstractmethod
    def create_tool(self) -> BaseTool:
        pass