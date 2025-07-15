import pytest
from unittest.mock import Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.navigate_to import NavigateTo
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_state import ToolState

TOOL_NAME_NAVIGATE_TO = "NavigateTo" # Based on class name default

@pytest.fixture
def mock_agent_context_navigate_to():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_navigate_standalone"
    return mock_context

@pytest.fixture
def navigate_to_tool_instance(mock_agent_context_navigate_to):
    tool = NavigateTo()
    tool.set_agent_id(mock_agent_context_navigate_to.agent_id) # Set agent_id for tests
    return tool

def test_tool_state_initialization(navigate_to_tool_instance: NavigateTo):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(navigate_to_tool_instance, 'tool_state')
    assert isinstance(navigate_to_tool_instance.tool_state, ToolState)
    assert navigate_to_tool_instance.tool_state == {}
    # Verify it's usable
    navigate_to_tool_instance.tool_state['navigation_history'] = ['a.com']
    assert navigate_to_tool_instance.tool_state['navigation_history'] == ['a.com']

# Definition Tests
def test_navigate_to_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_NAVIGATE_TO)
    assert definition is not None
    assert definition.name == TOOL_NAME_NAVIGATE_TO
    assert "Navigates a standalone browser instance" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 1
    param_url = schema.get_parameter("url")
    assert param_url is not None
    assert param_url.param_type == ParameterType.STRING
    assert param_url.required is True
    assert "fully qualified URL" in param_url.description

# Execute Tests
@pytest.mark.asyncio
async def test_execute_success(navigate_to_tool_instance: NavigateTo, mock_agent_context_navigate_to):
    url = "https://example.com"
    
    mock_playwright_page = AsyncMock()
    mock_response = AsyncMock()
    mock_response.ok = True
    mock_playwright_page.goto.return_value = mock_response

    with patch.object(navigate_to_tool_instance, 'initialize', AsyncMock()), \
         patch.object(navigate_to_tool_instance, 'close', AsyncMock()), \
         patch.object(navigate_to_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        result = await navigate_to_tool_instance.execute(mock_agent_context_navigate_to, url=url)
    
    assert result == f"Successfully navigated to {url}"
    mock_playwright_page.goto.assert_called_once_with(url, wait_until="domcontentloaded", timeout=60000)

@pytest.mark.asyncio
async def test_execute_navigation_fails_status(navigate_to_tool_instance: NavigateTo, mock_agent_context_navigate_to):
    url = "https://example.com/404"
    
    mock_playwright_page = AsyncMock()
    mock_response = AsyncMock()
    mock_response.ok = False
    mock_response.status = 404
    mock_playwright_page.goto.return_value = mock_response

    with patch.object(navigate_to_tool_instance, 'initialize', AsyncMock()), \
         patch.object(navigate_to_tool_instance, 'close', AsyncMock()), \
         patch.object(navigate_to_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        result = await navigate_to_tool_instance.execute(mock_agent_context_navigate_to, url=url)
    
    assert result == f"Navigation to {url} failed with status 404"

@pytest.mark.asyncio
async def test_execute_invalid_url_format(navigate_to_tool_instance: NavigateTo, mock_agent_context_navigate_to):
    url = "invalid-url-format" # Missing scheme
    with pytest.raises(ValueError, match="Invalid URL format"):
        await navigate_to_tool_instance.execute(mock_agent_context_navigate_to, url=url)

@pytest.mark.asyncio
async def test_execute_missing_url_arg(navigate_to_tool_instance: NavigateTo, mock_agent_context_navigate_to):
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_NAVIGATE_TO}'"):
        await navigate_to_tool_instance.execute(mock_agent_context_navigate_to) # url missing

@pytest.mark.asyncio
async def test_execute_playwright_error(navigate_to_tool_instance: NavigateTo, mock_agent_context_navigate_to):
    url = "https://example.com/playwright-error"
    
    mock_playwright_page = AsyncMock()
    mock_playwright_page.goto = AsyncMock(side_effect=Exception("Playwright goto failed"))

    with patch.object(navigate_to_tool_instance, 'initialize', AsyncMock()), \
         patch.object(navigate_to_tool_instance, 'close', AsyncMock()) as mock_close, \
         patch.object(navigate_to_tool_instance, 'page', new_callable=lambda: mock_playwright_page):

        with pytest.raises(RuntimeError, match="NavigateTo (standalone) failed for URL .* Playwright goto failed"):
            await navigate_to_tool_instance.execute(mock_agent_context_navigate_to, url=url)
        
        mock_close.assert_called_once()
