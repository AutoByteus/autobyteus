import pytest
from unittest.mock import AsyncMock, Mock, patch
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.utils.html_cleaner import CleaningMode
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_state import ToolState

TOOL_NAME_SESSION_READER = "WebPageReader" # From tool's get_name()

@pytest.fixture
def mock_agent_context_session_reader():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_session_reader"
    return mock_context

@pytest.fixture
def mock_shared_browser_session_reader(): # Specific fixture name
    session = AsyncMock(spec=SharedBrowserSession)
    session.page = AsyncMock()
    session.page.url = "https://mocked.page.url/reader"
    return session

@pytest.fixture
def webpage_reader_session_tool_default(mock_agent_context_session_reader): # Default config (THOROUGH)
    tool = BrowserSessionAwareWebPageReader()
    tool.set_agent_id(mock_agent_context_session_reader.agent_id)
    return tool

@pytest.fixture
def webpage_reader_session_tool_basic(mock_agent_context_session_reader): # BASIC config
    config = ToolConfig(params={'cleaning_mode': CleaningMode.BASIC.name})
    tool = BrowserSessionAwareWebPageReader(config=config)
    tool.set_agent_id(mock_agent_context_session_reader.agent_id)
    return tool

def test_tool_state_initialization(webpage_reader_session_tool_default: BrowserSessionAwareWebPageReader):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(webpage_reader_session_tool_default, 'tool_state')
    assert isinstance(webpage_reader_session_tool_default.tool_state, ToolState)
    assert webpage_reader_session_tool_default.tool_state == {}
    # Verify it's usable
    webpage_reader_session_tool_default.tool_state['read_count'] = 1
    assert webpage_reader_session_tool_default.tool_state['read_count'] == 1

# Definition Tests
def test_session_reader_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_SESSION_READER)
    assert definition is not None
    assert definition.name == TOOL_NAME_SESSION_READER
    assert "Reads and cleans the HTML content from the current page" in definition.description

    arg_schema = definition.argument_schema
    assert isinstance(arg_schema, ParameterSchema)
    assert len(arg_schema.parameters) == 1 # Only webpage_url for session mgmt
    assert arg_schema.get_parameter("webpage_url").required is True

    config_schema = definition.config_schema # Instantiation config
    assert isinstance(config_schema, ParameterSchema)
    assert len(config_schema.parameters) == 1
    cleaning_param = config_schema.get_parameter("cleaning_mode")
    assert cleaning_param is not None
    assert cleaning_param.default_value == "THOROUGH"

# Test perform_action
@pytest.mark.asyncio
async def test_perform_action_reads_and_cleans_content(
    webpage_reader_session_tool_default: BrowserSessionAwareWebPageReader, 
    mock_shared_browser_session_reader: SharedBrowserSession
):
    mock_html_content = "<html><head><title>Test</title></head><body><p>Hello Reader!</p><script>bad</script></body></html>"
    mock_shared_browser_session_reader.page.content.return_value = mock_html_content
    
    # Tool is THOROUGH by default
    result_content = await webpage_reader_session_tool_default.perform_action(
        mock_shared_browser_session_reader, 
        webpage_url="http://dummy.url/forperformaction" # Passed by base class
    )
    
    assert "Test Hello Reader!" in result_content # Approx. text after THOROUGH
    assert "<html" not in result_content.lower()
    assert "<script" not in result_content.lower()
    mock_shared_browser_session_reader.page.content.assert_called_once()

@pytest.mark.asyncio
async def test_perform_action_with_basic_cleaning(
    webpage_reader_session_tool_basic: BrowserSessionAwareWebPageReader, # Instance with BASIC cleaning
    mock_shared_browser_session_reader: SharedBrowserSession
):
    assert webpage_reader_session_tool_basic.cleaning_mode == CleaningMode.BASIC
    raw_html = "<html><body><script>alert('XSS')</script><b>Allowed Content</b></body></html>"
    mock_shared_browser_session_reader.page.content.return_value = raw_html

    with patch('autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader.clean') as mock_clean_func:
        mock_clean_func.return_value = "Cleaned with BASIC (session)"
        
        result = await webpage_reader_session_tool_basic.perform_action(
            mock_shared_browser_session_reader,
            webpage_url="http://dummy.url"
        )
        
        mock_clean_func.assert_called_once_with(raw_html, CleaningMode.BASIC)
        assert result == "Cleaned with BASIC (session)"

# Test full .execute()
@pytest.mark.asyncio
async def test_full_execute_with_session_mocking(
    webpage_reader_session_tool_default: BrowserSessionAwareWebPageReader, 
    mock_agent_context_session_reader: AgentContext,
    mock_shared_browser_session_reader: SharedBrowserSession
):
    mock_session_manager_instance = AsyncMock()
    mock_session_manager_instance.get_shared_browser_session.return_value = mock_shared_browser_session_reader
    # Mock page content for the session
    mock_shared_browser_session_reader.page.content.return_value = "<p>Session Page Content</p>"

    with patch('autobyteus.tools.browser.session_aware.browser_session_aware_tool.SharedBrowserSessionManager', return_value=mock_session_manager_instance):
        webpage_reader_session_tool_default.shared_browser_session_manager = mock_session_manager_instance

        result = await webpage_reader_session_tool_default.execute(
            mock_agent_context_session_reader,
            webpage_url="https://example.com/session_reader_target" # Required by schema
        )

    assert "Session Page Content" in result # After THOROUGH cleaning by default
    mock_shared_browser_session_reader.page.content.assert_called_once()
