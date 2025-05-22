import pytest
import os
from unittest.mock import Mock, AsyncMock, patch # Added Mock, AsyncMock, patch
from autobyteus.tools.browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker
from autobyteus.tools.tool_config_schema import ParameterType # For schema test

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def screenshot_taker_tool(): # Renamed fixture
    return WebPageScreenshotTaker() # Uses default config

@pytest.mark.asyncio
async def test_webpage_screenshot_taker(screenshot_taker_tool, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path
    url = "https://gemini.google.com/app/f851361aa822cfb8"
    file_name_arg = "gemini_test.png"
    file_path_to_save = tmp_path / file_name_arg # Use tmp_path

    # Mock Playwright interactions
    mock_page = AsyncMock()
    # Mock page.screenshot to simulate file creation
    async def mock_take_screenshot(path, full_page, type):
        with open(path, "wb") as f: # Simulate file creation
            f.write(b"dummy screenshot data")
        return None 
    mock_page.screenshot = AsyncMock(side_effect=mock_take_screenshot)


    with patch.object(WebPageScreenshotTaker, 'initialize', AsyncMock()) as mock_initialize, \
         patch.object(WebPageScreenshotTaker, 'close', AsyncMock()) as mock_close, \
         patch.object(WebPageScreenshotTaker, 'page', new_callable=lambda: mock_page):
        
        saved_file_path = await screenshot_taker_tool.execute(
            mock_agent_context, # Added mock_agent_context
            url=url, 
            file_path=str(file_path_to_save) # Pass full path for saving
        )
    
    # Assertions
    mock_initialize.assert_called_once()
    mock_page.goto.assert_called_once_with(url)
    mock_page.screenshot.assert_called_once_with(
        path=str(file_path_to_save), 
        full_page=screenshot_taker_tool.full_page, # from tool's default config
        type=screenshot_taker_tool.image_format # from tool's default config
    )
    mock_close.assert_called_once()
    
    assert saved_file_path == str(file_path_to_save)
    assert os.path.isfile(saved_file_path)
    with open(saved_file_path, "rb") as f:
        assert f.read() == b"dummy screenshot data"


def test_tool_usage_xml(screenshot_taker_tool):
    usage_xml = screenshot_taker_tool.tool_usage_xml()
    assert "WebPageScreenshotTaker: Takes a screenshot of a given webpage" in usage_xml
    assert '<command name="WebPageScreenshotTaker">' in usage_xml
    assert '<arg name="url">webpage_url</arg>' in usage_xml
    assert '<arg name="file_path">screenshot_file_path</arg>' in usage_xml

def test_get_config_schema(screenshot_taker_tool):
    schema = screenshot_taker_tool.get_config_schema()
    assert schema is not None
    
    full_page_param = schema.get_parameter("full_page")
    assert full_page_param is not None
    assert full_page_param.param_type == ParameterType.BOOLEAN
    assert full_page_param.default_value is True

    image_format_param = schema.get_parameter("image_format")
    assert image_format_param is not None
    assert image_format_param.param_type == ParameterType.ENUM
    assert image_format_param.default_value == "png"
