import pytest
from unittest.mock import Mock, AsyncMock, patch
from autobyteus.tools.browser.session_aware.browser_session_aware_navigate_to import BrowserSessionAwareNavigateTo
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext # For mock_agent_context
from autobyteus.tools.registry import default_tool_registry

TOOL_NAME_NAVIGATE_SESSION = "NavigateTo" # Based on overridden get_name()

@pytest.fixture
def mock_agent_context_navigate_session():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_nav_session"
    return mock_context

@pytest.fixture
def mock_shared_browser_session():
    session = AsyncMock(spec=SharedBrowserSession)
    session.page = AsyncMock() # Mock the page attribute
    return session

@pytest.fixture
def navigate_to_session_tool_instance(mock_agent_context_navigate_session):
    # This tool inherits from BrowserSessionAwareTool, which has its own __init__ logic
    # for shared_browser_session_manager.
    tool = BrowserSessionAwareNavigateTo()
    tool.set_agent_id(mock_agent_context_navigate_session.agent_id)
    return tool

def test_tool_state_initialization(navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(navigate_to_session_tool_instance, 'tool_state')
    assert isinstance(navigate_to_session_tool_instance.tool_state, dict)
    assert navigate_to_session_tool_instance.tool_state == {}
    # Verify it's usable
    navigate_to_session_tool_instance.tool_state['last_url'] = 'http://a.com'
    assert navigate_to_session_tool_instance.tool_state['last_url'] == 'http://a.com'

# Definition Tests
def test_navigate_to_session_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_NAVIGATE_SESSION)
    assert definition is not None
    assert definition.name == TOOL_NAME_NAVIGATE_SESSION
    assert "Navigates the shared browser session" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1
    param_url = schema.get_parameter("webpage_url") # Argument name from schema
    assert param_url is not None
    assert param_url.required is True

# Test perform_action directly, as _execute in base class handles session setup
@pytest.mark.asyncio
async def test_perform_action_success(
    navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo, 
    mock_shared_browser_session: SharedBrowserSession
):
    url = "https://example.com/session_nav"
    
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_shared_browser_session.page.goto.return_value = mock_response # Mock the goto call on the page

    result = await navigate_to_session_tool_instance.perform_action(mock_shared_browser_session, webpage_url=url)
    
    assert "executed successfully" in result
    mock_shared_browser_session.page.goto.assert_called_once_with(url, wait_until="networkidle", timeout=60000)

@pytest.mark.asyncio
async def test_perform_action_navigation_fails_status(
    navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo, 
    mock_shared_browser_session: SharedBrowserSession
):
    url = "https://example.com/session_404"
    
    mock_response = AsyncMock()
    mock_response.ok = False
    mock_response.status = 404
    mock_shared_browser_session.page.goto.return_value = mock_response

    result = await navigate_to_session_tool_instance.perform_action(mock_shared_browser_session, webpage_url=url)
    
    assert f"failed with status 404" in result

@pytest.mark.asyncio
async def test_perform_action_invalid_url_format(
    navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo, 
    mock_shared_browser_session: SharedBrowserSession
):
    url = "invalid-url"
    with pytest.raises(ValueError, match="Invalid URL format"):
        await navigate_to_session_tool_instance.perform_action(mock_shared_browser_session, webpage_url=url)

@pytest.mark.asyncio
async def test_perform_action_playwright_error(
    navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo, 
    mock_shared_browser_session: SharedBrowserSession
):
    url = "https://example.com/playwright_error_session"
    mock_shared_browser_session.page.goto.side_effect = Exception("Playwright session goto failed")

    result = await navigate_to_session_tool_instance.perform_action(mock_shared_browser_session, webpage_url=url)
    assert f"Error navigating to {url}: Playwright session goto failed" in result


# To test the full .execute(), we'd need to mock SharedBrowserSessionManager
# and its interactions within BrowserSessionAwareTool._execute.
# For now, focusing on perform_action as the tool's core logic.
@pytest.mark.asyncio
async def test_full_execute_missing_url_arg(
    navigate_to_session_tool_instance: BrowserSessionAwareNavigateTo, 
    mock_agent_context_navigate_session
):
    # This tests BaseTool.execute's validation
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_NAVIGATE_SESSION}'"):
        await navigate_to_session_tool_instance.execute(mock_agent_context_navigate_session) # webpage_url missing
