import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.agent.context import AgentContext 
from autobyteus.tools.registry import default_tool_registry # Added

@pytest.fixture
def mock_agent_context_ss(): 
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_ss_taker"
    return mock_context

@pytest.fixture
def screenshot_taker_tool_default(): 
    return WebPageScreenshotTaker()

@pytest.fixture
def screenshot_taker_tool_custom_config(): 
    config = ToolConfig(params={'full_page': False, 'image_format': 'jpeg'})
    return WebPageScreenshotTaker(config=config)

# Definition Tests
def test_get_name(screenshot_taker_tool_default: WebPageScreenshotTaker):
    assert screenshot_taker_tool_default.get_name() == "WebPageScreenshotTaker"

def test_get_description(screenshot_taker_tool_default: WebPageScreenshotTaker):
    desc = screenshot_taker_tool_default.get_description()
    assert "Takes a screenshot" in desc
    assert "saves it to the specified file path" in desc

def test_get_config_schema_for_instantiation(screenshot_taker_tool_default: WebPageScreenshotTaker):
    schema = screenshot_taker_tool_default.get_config_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 
    
    full_page_param = schema.get_parameter("full_page")
    assert full_page_param.default_value is True
    image_format_param = schema.get_parameter("image_format")
    assert image_format_param.default_value == "png"
    assert "jpeg" in image_format_param.enum_values

def test_get_argument_schema_for_execution(screenshot_taker_tool_default: WebPageScreenshotTaker):
    schema = screenshot_taker_tool_default.get_argument_schema()
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 
    
    url_param = schema.get_parameter("url")
    assert url_param.name == "url"
    assert url_param.required is True
    file_path_param = schema.get_parameter("file_path")
    assert file_path_param.name == "file_path"
    assert file_path_param.required is True
    assert file_path_param.param_type == ParameterType.STRING # MODIFIED from FILE_PATH

# Execute Tests
@pytest.mark.asyncio
async def test_execute_missing_args(screenshot_taker_tool_default: WebPageScreenshotTaker, mock_agent_context_ss):
    with pytest.raises(ValueError, match="Invalid arguments for tool 'WebPageScreenshotTaker'"):
        await screenshot_taker_tool_default.execute(mock_agent_context_ss, url="http://example.com") 

    with pytest.raises(ValueError, match="Invalid arguments for tool 'WebPageScreenshotTaker'"):
        await screenshot_taker_tool_default.execute(mock_agent_context_ss, file_path="test.png") 

@pytest.mark.asyncio
async def test_webpage_screenshot_taker_execute_default_config(screenshot_taker_tool_default: WebPageScreenshotTaker, mock_agent_context_ss, tmp_path):
    url_to_shot = "https://example.com/shot_default"
    file_path_arg = str(tmp_path / "screenshot_default.png")

    mock_playwright_page = AsyncMock()
    mock_playwright_page.screenshot = AsyncMock()

    with patch.object(screenshot_taker_tool_default, 'initialize', AsyncMock()) as mock_init, \
         patch.object(screenshot_taker_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(screenshot_taker_tool_default, 'page', new_callable=lambda: mock_playwright_page):
        
        os.makedirs(os.path.dirname(file_path_arg), exist_ok=True)

        returned_path = await screenshot_taker_tool_default.execute(
            mock_agent_context_ss, 
            url=url_to_shot, 
            file_path=file_path_arg
        )
    
    mock_init.assert_called_once()
    mock_playwright_page.goto.assert_called_once_with(url_to_shot, wait_until="networkidle", timeout=60000)
    mock_playwright_page.screenshot.assert_called_once_with(
        path=file_path_arg, 
        full_page=True, 
        type="png"      
    )
    mock_close.assert_called_once()
    assert returned_path == os.path.abspath(file_path_arg)

@pytest.mark.asyncio
async def test_webpage_screenshot_taker_execute_custom_config(screenshot_taker_tool_custom_config: WebPageScreenshotTaker, mock_agent_context_ss, tmp_path):
    assert screenshot_taker_tool_custom_config.full_page is False
    assert screenshot_taker_tool_custom_config.image_format == "jpeg"

    url_to_shot = "https://example.com/shot_custom"
    file_path_arg = str(tmp_path / "screenshot_custom.jpeg")

    mock_playwright_page = AsyncMock()
    mock_playwright_page.screenshot = AsyncMock()

    with patch.object(screenshot_taker_tool_custom_config, 'initialize', AsyncMock()), \
         patch.object(screenshot_taker_tool_custom_config, 'close', AsyncMock()), \
         patch.object(screenshot_taker_tool_custom_config, 'page', new_callable=lambda: mock_playwright_page):
        
        os.makedirs(os.path.dirname(file_path_arg), exist_ok=True)
        await screenshot_taker_tool_custom_config.execute(
            mock_agent_context_ss, 
            url=url_to_shot, 
            file_path=file_path_arg
        )
    
    mock_playwright_page.screenshot.assert_called_once_with(
        path=file_path_arg, 
        full_page=False, 
        type="jpeg"      
    )

@pytest.mark.asyncio
async def test_webpage_screenshot_taker_playwright_error(screenshot_taker_tool_default: WebPageScreenshotTaker, mock_agent_context_ss, tmp_path):
    url_to_shot = "https://error.example.com"
    file_path_arg = str(tmp_path / "error.png")
    
    mock_playwright_page = AsyncMock()
    mock_playwright_page.goto = AsyncMock(side_effect=Exception("Playwright screenshot goto failed"))

    with patch.object(screenshot_taker_tool_default, 'initialize', AsyncMock()), \
         patch.object(screenshot_taker_tool_default, 'close', AsyncMock()) as mock_close, \
         patch.object(screenshot_taker_tool_default, 'page', new_callable=lambda: mock_playwright_page):

        with pytest.raises(RuntimeError, match="WebPageScreenshotTaker failed for URL .* Playwright screenshot goto failed"):
            await screenshot_taker_tool_default.execute(mock_agent_context_ss, url=url_to_shot, file_path=file_path_arg)
        
        mock_close.assert_called_once()
