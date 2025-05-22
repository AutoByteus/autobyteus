import pytest
import os # Added os for abspath
from unittest.mock import AsyncMock, Mock # Added Mock

from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker
from autobyteus.tools.tool_config_schema import ParameterType # For schema test

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def screenshot_taker_tool(): # Renamed fixture
    return BrowserSessionAwareWebPageScreenshotTaker()

@pytest.mark.asyncio
async def test_browser_session_aware_webpage_screenshot_taker_execute(screenshot_taker_tool, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path
    # Mock the shared_browser_session_manager and shared_session
    mock_shared_session = AsyncMock()
    # Mock the screenshot method
    mock_shared_session.page.screenshot = AsyncMock()

    mock_session_manager = Mock()
    mock_session_manager.get_shared_browser_session.return_value = mock_shared_session
    mock_session_manager.create_shared_browser_session = AsyncMock()

    screenshot_taker_tool.shared_browser_session_manager = mock_session_manager
    
    # Use tmp_path for a temporary file
    file_name_arg = "screenshot.png" 
    temp_file_path = tmp_path / file_name_arg # Save to temp dir

    result = await screenshot_taker_tool.execute(
        mock_agent_context, # Added mock_agent_context
        webpage_url="https://www.xiaohongshu.com/explore", # Changed url to webpage_url
        file_name=str(temp_file_path) # Changed file_path to file_name, pass full path for saving
    )

    expected_path = os.path.abspath(str(temp_file_path))
    assert result == expected_path
    # Check if screenshot method was called correctly
    mock_shared_session.page.screenshot.assert_called_once_with(
        path=str(temp_file_path), 
        full_page=screenshot_taker_tool.full_page, # from tool's default
        type=screenshot_taker_tool.image_format # from tool's default
    )

def test_tool_usage_xml(screenshot_taker_tool):
    usage_xml = screenshot_taker_tool.tool_usage_xml()
    assert 'WebPageScreenshotTaker: Takes a screenshot of a given webpage' in usage_xml
    assert '<command name="WebPageScreenshotTaker">' in usage_xml
    assert '<arg name="webpage_url">url_to_screenshot</arg>' in usage_xml
    assert '<arg name="file_name">screenshot_file_name</arg>' in usage_xml

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
    assert "png" in image_format_param.enum_values
    assert "jpeg" in image_format_param.enum_values
