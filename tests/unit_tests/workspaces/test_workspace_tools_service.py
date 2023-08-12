import pytest
from unittest.mock import patch, Mock
from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from src.workspaces.workspace_tools_service import WorkspaceToolsService
from src.workspaces.setting.workspace_setting import WorkspaceSetting

@pytest.fixture
def service():
    return WorkspaceToolsService()

@pytest.fixture
def mock_registry_with_setting():
    mock_setting = Mock(spec=WorkspaceSetting)
    mock_registry = Mock()
    mock_registry.get_setting.return_value = mock_setting
    return mock_registry

@pytest.fixture
def mock_registry_without_setting():
    mock_registry = Mock()
    mock_registry.get_setting.return_value = None
    return mock_registry

def test_refactor_workspace_missing_setting(service: WorkspaceToolsService, mock_registry_without_setting, caplog):
    """
    Test refactoring a workspace with missing workspace setting.
    """
    with patch.object(service, "setting_registry", mock_registry_without_setting):
        service.refactor_workspace("/path/to/workspace")
        
    # Check if the appropriate warning message is in the logs
    expected_warning = f"No workspace setting found for /path/to/workspace. Refactoring skipped."
    assert expected_warning in caplog.text


def test_refactor_workspace_with_setting(service: WorkspaceToolsService, mock_registry_with_setting):
    """
    Test refactoring a workspace with an available workspace setting.
    """
    with patch.object(service, "setting_registry", mock_registry_with_setting):
        with patch("src.workspaces.workspace_tools_service.WorkspaceRefactorer") as MockRefactorer:
            mock_instance = MockRefactorer.return_value
            service.refactor_workspace("/path/to/workspace")
            mock_instance.execute.assert_called_once()

def test_index_workspace(service):
    """
    Test indexing a workspace.
    """
    # Since it's a placeholder method, ensure it doesn't raise exceptions
    service.index_workspace("/path/to/workspace")

def test_get_available_tools(service):
    """
    Test fetching the names of all available workspace tools.
    """

    # Define an example tool for the purpose of this test
    class TestTool(BaseWorkspaceTool):
        name = "TestTool"

        def execute(self):
            pass

    tools = service.get_available_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0  # Ensure at least one tool is registered
    assert "TestTool" in tools  # Ensure our test tool is registered
