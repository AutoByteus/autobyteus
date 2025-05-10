# file: autobyteus/tools/factory/tool_factory.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool

class ToolFactory():
    def create_tool(self) -> "BaseTool":
        pass
