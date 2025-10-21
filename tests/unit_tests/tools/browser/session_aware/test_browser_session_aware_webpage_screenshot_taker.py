import pytest
import os
from unittest.mock import AsyncMock, Mock, patch
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_state import ToolState

TOOL_NAME_SESSION_SS_TAKER = "take_webpage_screenshot"

@pytest.fixture
def mock_agent_context_session_ss():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_session_ss"
    return mock_context

@pytest.fixture
def mock_shared_browser_session_ss(): # Specific fixture
    session = AsyncMock(spec=SharedBrowserSession)
    session.page = AsyncMock()
    session.page.url = "https://mocked.page.url/ss_taker"
    return session

@pytest.fixture
def ss_taker_session_tool_default(mock_agent_context_session_ss): # Default config
    tool = BrowserSessionAwareWebPageScreenshotTaker()
    tool.set_agent_id(mock_agent_context_session_ss.agent_id)
    return tool

@pytest.fixture
def ss_taker_session_tool_custom(mock_agent_context_session_ss): # Custom config
    config = ToolConfig(params={'full_page': False, 'image_format': 'jpeg'})
    tool = BrowserSessionAwareWebPageScreenshotTaker(config=config)
    tool.set_agent_id(mock_agent_context_session_ss.agent_id)
    return tool

def test_tool_state_initialization(ss_taker_session_tool_default: BrowserSessionAwareWebPageScreenshotTaker):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(ss_taker_session_tool_default, 'tool_state')
    assert isinstance(ss_taker_session_tool_default.tool_state, ToolState)
    assert ss_taker_session_tool_default.tool_state == {}
    # Verify it's usable
    ss_taker_session_tool_default.tool_state['screenshot_count'] = 1
    assert ss_taker_session_tool_default.tool_state['screenshot_count'] == 1

# Definition Tests
def test_session_ss_taker_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_SESSION_SS_TAKER)
    assert definition is not None
    assert definition.name == TOOL_NAME_SESSION_SS_TAKER
    assert "Takes a screenshot of the current page in a shared browser session" in definition.description

    arg_schema = definition.argument_schema
    assert isinstance(arg_schema, ParameterSchema)
    assert len(arg_schema.parameters) == 2 # webpage_url, file_name
    assert arg_schema.get_parameter("webpage_url").required is True
    file_name_param = arg_schema.get_parameter("file_name")
    assert file_name_param.required is True
    assert file_name_param.param_type == ParameterType.STRING 

    config_schema = definition.config_schema # Instantiation config
    assert isinstance(config_schema, ParameterSchema)
    assert len(config_schema.parameters) == 2 # full_page, image_format
    assert config_schema.get_parameter("full_page").default_value is True
    assert config_schema.get_parameter("image_format").default_value == "png"

# Test perform_action
@pytest.mark.asyncio
async def test_perform_action_default_settings(
    ss_taker_session_tool_default: BrowserSessionAwareWebPageScreenshotTaker, 
    mock_shared_browser_session_ss: SharedBrowserSession,
    tmp_path
):
    file_to_save = str(tmp_path / "session_ss_default.png")
    
    returned_path = await ss_taker_session_tool_default.perform_action(
        mock_shared_browser_session_ss, 
        file_name=file_to_save,
        webpage_url="http://dummy.url/forperformaction" 
    )
    
    assert returned_path == os.path.abspath(file_to_save)
    mock_shared_browser_session_ss.page.screenshot.assert_called_once_with(
        path=file_to_save,
        full_page=True,
        type="png"
    )
    assert os.path.isdir(os.path.dirname(file_to_save)) 

@pytest.mark.asyncio
async def test_perform_action_custom_settings(
    ss_taker_session_tool_custom: BrowserSessionAwareWebPageScreenshotTaker, 
    mock_shared_browser_session_ss: SharedBrowserSession,
    tmp_path
):
    file_to_save = str(tmp_path / "session_ss_custom.jpeg")
    assert ss_taker_session_tool_custom.full_page is False
    assert ss_taker_session_tool_custom.image_format == "jpeg"

    returned_path = await ss_taker_session_tool_custom.perform_action(
        mock_shared_browser_session_ss, 
        file_name=file_to_save,
        webpage_url="http://dummy.url"
    )
    assert returned_path == os.path.abspath(file_to_save)
    mock_shared_browser_session_ss.page.screenshot.assert_called_once_with(
        path=file_to_save,
        full_page=False,
        type="jpeg"
    )

# Test full .execute()
@pytest.mark.asyncio
async def test_full_execute_with_session_mocking(
    ss_taker_session_tool_default: BrowserSessionAwareWebPageScreenshotTaker, 
    mock_agent_context_session_ss: AgentContext,
    mock_shared_browser_session_ss: SharedBrowserSession,
    tmp_path
):
    file_to_save_execute = str(tmp_path / "session_ss_execute.png")

    mock_session_manager_instance = AsyncMock()
    mock_session_manager_instance.get_shared_browser_session.return_value = mock_shared_browser_session_ss
    
    with patch('autobyteus.tools.browser.session_aware.browser_session_aware_tool.SharedBrowserSessionManager', return_value=mock_session_manager_instance):
        ss_taker_session_tool_default.shared_browser_session_manager = mock_session_manager_instance

        result_path = await ss_taker_session_tool_default.execute(
            mock_agent_context_session_ss,
            webpage_url="https://example.com/session_ss_target", 
            file_name=file_to_save_execute
        )

    assert result_path == os.path.abspath(file_to_save_execute)
    mock_shared_browser_session_ss.page.screenshot.assert_called_once()
