import pytest
from unittest.mock import Mock, AsyncMock, patch # Added Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.html_cleaner import CleaningMode
from autobyteus.tools.tool_config import ToolConfig # Added ToolConfig import
from autobyteus.tools.tool_config_schema import ParameterType # For schema test

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def webpage_reader_tool(): # Renamed fixture and corrected instantiation
    # Corrected instantiation to use ToolConfig
    return WebPageReader(config=ToolConfig(params={'cleaning_mode': CleaningMode.STANDARD}))

@pytest.mark.asyncio
async def test_webpage_reader(webpage_reader_tool, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path
    url = "https://pubmed.ncbi.nlm.nih.gov/34561271/"
    
    # Mock Playwright interactions
    mock_page = AsyncMock()
    mock_page.content.return_value = "<html><body>Mocked Page Content for PubMed</body></html>"

    with patch.object(WebPageReader, 'initialize', AsyncMock()) as mock_initialize, \
         patch.object(WebPageReader, 'close', AsyncMock()) as mock_close, \
         patch.object(WebPageReader, 'page', new_callable=lambda: mock_page):

        page_content = await webpage_reader_tool.execute(mock_agent_context, url=url) # Added mock_agent_context
    
    # Assertions
    mock_initialize.assert_called_once()
    mock_page.goto.assert_called_once_with(url, timeout=0)
    mock_page.content.assert_called_once()
    mock_close.assert_called_once()

    assert "here is the html of the web page" in page_content
    assert "<WebPageContentStart>" in page_content
    # STANDARD cleaning should remove html/body tags but keep content
    assert "Mocked Page Content for PubMed" in page_content 
    assert "<html" not in page_content.lower() 
    assert "<body" not in page_content.lower()
    assert "</WebPageContentEnd>" in page_content
    
    # Save the page content to a file (optional for test logic)
    file_name = tmp_path / "paper_details_test.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")

def test_tool_usage_xml(webpage_reader_tool):
    usage_xml = webpage_reader_tool.tool_usage_xml()
    assert "WebPageReader: Reads the HTML content from a given webpage." in usage_xml
    assert '<command name="WebPageReader">' in usage_xml
    assert '<arg name="url">webpage_url</arg>' in usage_xml

def test_get_config_schema(webpage_reader_tool):
    schema = webpage_reader_tool.get_config_schema()
    assert schema is not None
    cleaning_mode_param = schema.get_parameter("cleaning_mode")
    assert cleaning_mode_param is not None
    assert cleaning_mode_param.param_type == ParameterType.ENUM
    assert cleaning_mode_param.default_value == "THOROUGH" # Default in schema
    # The tool instance was created with STANDARD, but schema reflects defaults
