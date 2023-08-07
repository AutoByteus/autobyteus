import pytest
from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool

def test_base_workspace_tool_abstract_nature():
    """
    Test that BaseWorkspaceTool cannot be instantiated directly.
    """
    with pytest.raises(TypeError) as excinfo:
        instance = BaseWorkspaceTool()
    assert "Can't instantiate abstract class BaseWorkspaceTool" in str(excinfo.value)

def test_tool_without_execute_raises_error():
    """
    Test that a subclass without the 'execute' method implementation raises an error.
    """
    class ToolWithoutExecute(BaseWorkspaceTool):
        pass

    with pytest.raises(TypeError) as excinfo:
        instance = ToolWithoutExecute()
    assert "Can't instantiate abstract class ToolWithoutExecute" in str(excinfo.value)

def test_tool_name_registration():
    """
    Test that when a subclass of BaseWorkspaceTool with a defined name is created, 
    the name gets added to the list of available tools.
    """
    class ExampleTool(BaseWorkspaceTool):
        name = "ExampleTool"

        def execute(self):
            pass

    assert "ExampleTool" in BaseWorkspaceTool.get_all_tools()
