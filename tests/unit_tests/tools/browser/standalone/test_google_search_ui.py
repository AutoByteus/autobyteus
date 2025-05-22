import pytest
from unittest.mock import Mock, AsyncMock, patch # Added Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch
from autobyteus.tools.tool_config_schema import ParameterType # For schema test

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def google_search_tool(): # Renamed fixture
    return GoogleSearch()

@pytest.mark.asyncio
async def test_google_search(google_search_tool, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path
    search_query = "The Shawshank Redemption movie poster"
    
    # Mock Playwright interactions
    mock_page = AsyncMock()
    mock_textarea = AsyncMock()
    mock_search_result_div = AsyncMock()

    # Configure mocks
    mock_page.locator.return_value = mock_textarea
    mock_page.wait_for_selector.return_value = mock_search_result_div
    mock_search_result_div.inner_html.return_value = "<html><body>Mocked Search Results for Shawshank</body></html>"
    
    # Patch the UIIntegrator's initialize and close methods, and the page property
    with patch.object(GoogleSearch, 'initialize', AsyncMock()) as mock_initialize, \
         patch.object(GoogleSearch, 'close', AsyncMock()) as mock_close, \
         patch.object(GoogleSearch, 'page', new_callable=lambda: mock_page): # Patch page property directly
        
        # Call execute
        search_results = await google_search_tool.execute(mock_agent_context, query=search_query) # Added mock_agent_context
    
    # Assertions
    mock_initialize.assert_called_once()
    mock_page.goto.assert_called_once_with('https://www.google.com/')
    mock_page.locator.assert_called_once_with(google_search_tool.text_area_selector)
    mock_textarea.click.assert_called_once()
    mock_page.type.assert_called_once_with(google_search_tool.text_area_selector, search_query)
    mock_page.keyboard.press.assert_called_once_with('Enter')
    mock_page.wait_for_load_state.assert_called_once()
    mock_page.wait_for_selector.assert_called_once_with('#search', state="visible", timeout=10000)
    mock_search_result_div.inner_html.assert_called_once()
    mock_close.assert_called_once()

    assert "here is the google search result html" in search_results
    assert "<GoogleSearchResultStart>" in search_results
    assert "Mocked Search Results for Shawshank" in search_results # Check if cleaned content is present
    assert "</GoogleSearchResultEnd>" in search_results
       
    # Save the page content to a file (optional for test logic if asserting content)
    file_name = tmp_path / "shawshank_search_test.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(search_results)
    print(f"Search results saved to {file_name}")

def test_tool_usage(google_search_tool): # Changed from test_google_search to test_tool_usage
    usage_xml = google_search_tool.tool_usage_xml() # Call tool_usage_xml
    assert 'GoogleSearch: Searches the internet for information.' in usage_xml
    assert '<command name="GoogleSearch">' in usage_xml
    assert '<arg name="query">search query</arg>' in usage_xml

def test_get_config_schema(google_search_tool):
    schema = google_search_tool.get_config_schema()
    assert schema is not None
    cleaning_mode_param = schema.get_parameter("cleaning_mode")
    assert cleaning_mode_param is not None
    assert cleaning_mode_param.param_type == ParameterType.ENUM
    assert cleaning_mode_param.default_value == "THOROUGH"
    assert "BASIC" in cleaning_mode_param.enum_values
