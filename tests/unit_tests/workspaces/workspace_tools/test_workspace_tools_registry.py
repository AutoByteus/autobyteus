import pytest
from autobyteus.workspaces.workspace_tools.workspace_tools_registry import WorkspaceToolsRegistry
from autobyteus.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool

# Mock classes for testing purposes
class MockValidTool1(BaseWorkspaceTool):
    pass

class MockValidTool2(BaseWorkspaceTool):
    pass

class MockInvalidTool:
    pass

# Since WorkspaceToolsRegistry is a Singleton, we need to reset its state before each test
@pytest.fixture(autouse=True)
def reset_registry():
    WorkspaceToolsRegistry._tools.clear()

def test_register_single_valid_tool():
    """
    GIVEN a valid workspace tool
    WHEN the tool is registered using register_tool
    THEN it should be added to the registry
    """
    WorkspaceToolsRegistry.register_tool(MockValidTool1)
    assert MockValidTool1 in WorkspaceToolsRegistry.get_all_tools()

def test_register_multiple_valid_tools():
    """
    GIVEN multiple valid workspace tools
    WHEN the tools are registered using register_tool
    THEN all tools should be added to the registry
    """
    WorkspaceToolsRegistry.register_tool(MockValidTool1, MockValidTool2)
    assert MockValidTool1 in WorkspaceToolsRegistry.get_all_tools()
    assert MockValidTool2 in WorkspaceToolsRegistry.get_all_tools()

def test_register_invalid_tool_raises_value_error():
    """
    GIVEN an invalid workspace tool (not a subclass of BaseWorkspaceTool)
    WHEN trying to register this tool
    THEN a ValueError should be raised
    """
    with pytest.raises(ValueError, match="Tool MockInvalidTool is not a subclass of BaseWorkspaceTool"):
        WorkspaceToolsRegistry.register_tool(MockInvalidTool)

def test_get_all_tools_returns_all_registered_tools():
    """
    GIVEN a set of registered tools
    WHEN get_all_tools is called
    THEN it should return all the registered tools
    """
    WorkspaceToolsRegistry.register_tool(MockValidTool1, MockValidTool2)
    assert set(WorkspaceToolsRegistry.get_all_tools()) == {MockValidTool1, MockValidTool2}
