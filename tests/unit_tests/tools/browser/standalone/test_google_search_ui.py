import pytest
from unittest.mock import Mock, AsyncMock, patch
import xml.sax.saxutils
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated
from autobyteus.tools.tool_config import ToolConfig # For testing instantiation
from autobyteus.utils.html_cleaner import CleaningMode
from autobyteus.tools.tool_state import ToolState


@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_google"
    return mock_context

@pytest.fixture
def google_search_tool_default(): # Default instantiation
    return GoogleSearch()

@pytest.fixture
def google_search_tool_custom_config(): # With custom instantiation config
    config = ToolConfig(params={'cleaning_mode': CleaningMode.BASIC.name}) # Pass enum name as string
    return GoogleSearch(config=config)

def test_tool_state_initialization(google_search_tool_default: GoogleSearch):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(google_search_tool_default, 'tool_state')
    assert isinstance(google_search_tool_default.tool_state, ToolState)
    assert google_search_tool_default.tool_state == {}
    # Verify it's usable
    google_search_tool_default.tool_state['search_count'] = 1
    assert google_search_tool_default.tool_state['search_count'] == 1

def test_get_name(google_search_tool_default: GoogleSearch):
    assert google_search_tool_default.get_name() == "GoogleSearch"

def test_get_description(google_search_tool_default: GoogleSearch):
    desc = google_search_tool_default.get_description()
    assert "Searches Google" in desc
    assert "cleaned HTML search results" in desc

def test_get_config_schema_for_instantiation(google_search_tool_default: GoogleSearch):
    schema = google_search_tool_default.get_config_schema()
    assert isinstance(schema, ParameterSchema)
    param = schema.get_parameter("cleaning_mode")
    assert isinstance(param, ParameterDefinition)
    assert param.param_type == ParameterType.ENUM
    assert param.default_value == "THOROUGH"
    assert "BASIC" in param.enum_values
    assert "THOROUGH" in param.enum_values

def test_get_argument_schema_for_execution(google_search_tool_default: GoogleSearch):
    schema = google_search_tool_default.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    param = schema.get_parameter("query")
    assert isinstance(param, ParameterDefinition)
    assert param.name == "query"
    assert param.param_type == ParameterType.STRING
    assert param.required is True

@pytest.mark.asyncio
async def test_execute_missing_query_arg(google_search_tool_default: GoogleSearch, mock_agent_context):
    with pytest.raises(ValueError, match="Invalid arguments for tool 'GoogleSearch'"):
        await google_search_tool_default.execute(mock_agent_context) # No 'query'

@pytest.mark.asyncio
async def test_google_search_execute_successful(google_search_tool_default: GoogleSearch, mock_agent_context, tmp_path):
    search_query = "The Shawshank Redemption movie poster"
    
    mock_playwright_page = AsyncMock()
    mock_textarea_locator = AsyncMock()
    mock_search_results_div_locator = AsyncMock()

    # Configure mock returns
    mock_playwright_page.locator.return_value = mock_textarea_locator # For query input
    # wait_for_selector for search results div
    mock_playwright_page.wait_for_selector.return_value = mock_search_results_div_locator 
    mock_search_results_div_locator.inner_html.return_value = "<html><body>Mocked Search Results for Shawshank Redemption</body></html>"
    
    # Patch the UIIntegrator methods directly on the instance for this test
    # or on the class if these are always the same mocks.
    # For GoogleSearch, initialize and close are part of its lifecycle.
    # The `page` attribute is provided by UIIntegrator.
    with patch.object(google_search_tool_default, 'initialize', AsyncMock()) as mock_init, \
         patch.object(google_search_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(google_search_tool_default, 'page', new_callable=lambda: mock_playwright_page): # Make page a property mock

        search_results_html = await google_search_tool_default.execute(mock_agent_context, query=search_query)
    
    mock_init.assert_called_once()
    mock_playwright_page.goto.assert_called_once_with('https://www.google.com/')
    mock_playwright_page.locator.assert_called_once_with(google_search_tool_default.text_area_selector)
    mock_textarea_locator.click.assert_called_once()
    mock_playwright_page.type.assert_called_once_with(google_search_tool_default.text_area_selector, search_query)
    mock_playwright_page.keyboard.press.assert_called_once_with('Enter')
    mock_playwright_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=15000)
    mock_playwright_page.wait_for_selector.assert_called_once_with('#search', state="visible", timeout=10000)
    mock_search_results_div_locator.inner_html.assert_called_once() # Check that inner_html was called
    mock_close.assert_called_once()

    assert "here is the google search result html" in search_results_html
    assert "<GoogleSearchResultStart>" in search_results_html
    # Default cleaning is THOROUGH, so HTML tags should be mostly gone
    assert "Mocked Search Results for Shawshank Redemption" in search_results_html 
    assert "<html" not in search_results_html.lower() # Check cleaning effect
    assert "</GoogleSearchResultEnd>" in search_results_html
       
    file_name = tmp_path / "shawshank_search_test_results.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(search_results_html)

@pytest.mark.asyncio
async def test_google_search_custom_cleaning_mode(google_search_tool_custom_config: GoogleSearch, mock_agent_context):
    # google_search_tool_custom_config is initialized with CleaningMode.BASIC
    assert google_search_tool_custom_config.cleaning_mode == CleaningMode.BASIC
    search_query = "test query"

    mock_playwright_page = AsyncMock()
    mock_playwright_page.locator.return_value = AsyncMock()
    mock_playwright_page.wait_for_selector.return_value.inner_html.return_value = "<html><body><script>alert('XSS')</script><b>Allowed Content</b></body></html>"

    with patch.object(google_search_tool_custom_config, 'initialize', AsyncMock()), \
         patch.object(google_search_tool_custom_config, 'close', AsyncMock()), \
         patch.object(google_search_tool_custom_config, 'page', new_callable=lambda: mock_playwright_page):

        # Mock the 'clean' function to verify it's called with the correct mode
        with patch('autobyteus.tools.browser.standalone.google_search_ui.clean') as mock_clean_func:
            mock_clean_func.return_value = "Cleaned with BASIC mode" # Mock its output
            
            await google_search_tool_custom_config.execute(mock_agent_context, query=search_query)
            
            # Assert that clean was called with CleaningMode.BASIC
            mock_clean_func.assert_called_once_with(
                "<html><body><script>alert('XSS')</script><b>Allowed Content</b></body></html>",
                mode=CleaningMode.BASIC
            )

@pytest.mark.asyncio
async def test_google_search_playwright_error(google_search_tool_default: GoogleSearch, mock_agent_context):
    search_query = "error test"
    
    mock_playwright_page = AsyncMock()
    # Simulate an error during Playwright operations, e.g., page.goto fails
    mock_playwright_page.goto = AsyncMock(side_effect=Exception("Playwright navigation failed"))

    with patch.object(google_search_tool_default, 'initialize', AsyncMock()), \
         patch.object(google_search_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(google_search_tool_default, 'page', new_callable=lambda: mock_playwright_page):

        with pytest.raises(RuntimeError, match="GoogleSearch failed for query 'error test': Playwright navigation failed"):
            await google_search_tool_default.execute(mock_agent_context, query=search_query)
        
        mock_close.assert_called_once()
