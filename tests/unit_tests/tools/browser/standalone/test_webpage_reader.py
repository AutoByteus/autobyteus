import pytest
from unittest.mock import Mock, AsyncMock, patch
import xml.sax.saxutils
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.utils.html_cleaner import CleaningMode
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.tool_state import ToolState

@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_wp_reader"
    return mock_context

@pytest.fixture
def webpage_reader_tool_default(): # Default instantiation (THOROUGH cleaning)
    return WebPageReader()

@pytest.fixture
def webpage_reader_tool_basic_config(): # Basic cleaning via instantiation config
    config = ToolConfig(params={'cleaning_mode': CleaningMode.BASIC.name})
    return WebPageReader(config=config)

def test_tool_state_initialization(webpage_reader_tool_default: WebPageReader):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(webpage_reader_tool_default, 'tool_state')
    assert isinstance(webpage_reader_tool_default.tool_state, ToolState)
    assert webpage_reader_tool_default.tool_state == {}
    # Verify it's usable
    webpage_reader_tool_default.tool_state['last_url_read'] = 'http://b.com'
    assert webpage_reader_tool_default.tool_state['last_url_read'] == 'http://b.com'

def test_get_name(webpage_reader_tool_default: WebPageReader):
    assert webpage_reader_tool_default.get_name() == "read_webpage"

def test_get_description(webpage_reader_tool_default: WebPageReader):
    desc = webpage_reader_tool_default.get_description()
    assert "Reads and cleans the HTML content" in desc

def test_get_config_schema_for_instantiation(webpage_reader_tool_default: WebPageReader):
    schema = webpage_reader_tool_default.get_config_schema()
    assert isinstance(schema, ParameterSchema)
    param = schema.get_parameter("cleaning_mode")
    assert isinstance(param, ParameterDefinition)
    assert param.param_type == ParameterType.ENUM
    assert param.default_value == "THOROUGH"

def test_get_argument_schema_for_execution(webpage_reader_tool_default: WebPageReader):
    schema = webpage_reader_tool_default.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    param = schema.get_parameter("url")
    assert isinstance(param, ParameterDefinition)
    assert param.name == "url"
    assert param.required is True

@pytest.mark.asyncio
async def test_execute_missing_url_arg(webpage_reader_tool_default: WebPageReader, mock_agent_context):
    with pytest.raises(ValueError, match="Invalid arguments for tool 'read_webpage'"):
        await webpage_reader_tool_default.execute(mock_agent_context)

@pytest.mark.asyncio
async def test_webpage_reader_execute_successful_thorough_cleaning(webpage_reader_tool_default: WebPageReader, mock_agent_context, tmp_path):
    url = "https://example.com/article"
    
    mock_playwright_page = AsyncMock()
    mock_playwright_page.content.return_value = "<html><head><title>Title</title></head><body><h1>A Heading</h1><p>Some text. <a href='#'>Link</a></p><script>alert(1)</script></body></html>"
    
    with patch.object(webpage_reader_tool_default, 'initialize', AsyncMock()) as mock_init, \
         patch.object(webpage_reader_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(webpage_reader_tool_default, 'page', new_callable=lambda: mock_playwright_page):

        page_content_result = await webpage_reader_tool_default.execute(mock_agent_context, url=url)
    
    mock_init.assert_called_once()
    mock_playwright_page.goto.assert_called_once_with(url, timeout=60000, wait_until="domcontentloaded")
    mock_playwright_page.content.assert_called_once()
    mock_close.assert_called_once()

    assert "here is the html of the web page" in page_content_result
    assert "<WebPageContentStart>" in page_content_result
    # THOROUGH cleaning results
    assert "Title A Heading Some text. Link" in page_content_result # Approximate text extraction
    assert "<html" not in page_content_result.lower()
    assert "<script" not in page_content_result.lower()
    assert "<h1" not in page_content_result.lower() # Tags removed by THOROUGH
    assert "</WebPageContentEnd>" in page_content_result
    
    file_name = tmp_path / "webpage_reader_test.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content_result)

@pytest.mark.asyncio
async def test_webpage_reader_execute_basic_cleaning(webpage_reader_tool_basic_config: WebPageReader, mock_agent_context):
    # webpage_reader_tool_basic_config is initialized with CleaningMode.BASIC
    assert webpage_reader_tool_basic_config.cleaning_mode == CleaningMode.BASIC
    url = "https://example.com/basic"
    
    raw_html = "<html><body><script>alert('XSS')</script><b>Allowed Content</b> <style>.foo{}</style></body></html>"
    mock_playwright_page = AsyncMock()
    mock_playwright_page.content.return_value = raw_html

    with patch.object(webpage_reader_tool_basic_config, 'initialize', AsyncMock()), \
         patch.object(webpage_reader_tool_basic_config, 'close', AsyncMock()), \
         patch.object(webpage_reader_tool_basic_config, 'page', new_callable=lambda: mock_playwright_page):

        # Mock the 'clean' function to verify it's called with the correct mode
        with patch('autobyteus.tools.browser.standalone.webpage_reader.clean') as mock_clean_func:
            mock_clean_func.return_value = "Cleaned with BASIC mode test" # Mock its output
            
            result = await webpage_reader_tool_basic_config.execute(mock_agent_context, url=url)
            
            mock_clean_func.assert_called_once_with(
                raw_html,
                mode=CleaningMode.BASIC
            )
            assert "Cleaned with BASIC mode test" in result

@pytest.mark.asyncio
async def test_webpage_reader_playwright_error(webpage_reader_tool_default: WebPageReader, mock_agent_context):
    url = "https://error.example.com"
    
    mock_playwright_page = AsyncMock()
    mock_playwright_page.goto = AsyncMock(side_effect=Exception("Playwright goto failed"))

    with patch.object(webpage_reader_tool_default, 'initialize', AsyncMock()), \
         patch.object(webpage_reader_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(webpage_reader_tool_default, 'page', new_callable=lambda: mock_playwright_page):

        with pytest.raises(RuntimeError, match="read_webpage failed for URL .* Playwright goto failed"):
            await webpage_reader_tool_default.execute(mock_agent_context, url=url)
        
        mock_close.assert_called_once()
