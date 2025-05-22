import pytest
from unittest.mock import AsyncMock, Mock # Added Mock

from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.tools.tool_config_schema import ParameterType # For schema test

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def webpage_reader_tool(): # Renamed fixture to avoid conflict with import
    return BrowserSessionAwareWebPageReader()

@pytest.mark.asyncio
async def test_browser_session_aware_webpage_reader_execute(webpage_reader_tool, mock_agent_context): # Added mock_agent_context
    # Mock the shared_browser_session_manager and shared_session
    mock_shared_session = AsyncMock()
    mock_shared_session.page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
    
    mock_session_manager = Mock()
    mock_session_manager.get_shared_browser_session.return_value = mock_shared_session
    mock_session_manager.create_shared_browser_session = AsyncMock() # Needed if session is not found

    webpage_reader_tool.shared_browser_session_manager = mock_session_manager

    # Test with webpage_url for session creation if needed by base class
    result_content = await webpage_reader_tool.execute(
        mock_agent_context, # Added mock_agent_context
        webpage_url="https://www.xiaohongshu.com/explore" # Changed url to webpage_url
    )
    
    # Basic assertion, assuming default THOROUGH cleaning will simplify HTML
    assert "Test Content" in result_content 
    assert "<html" not in result_content.lower() # Example of thorough cleaning
    assert "<body" not in result_content.lower() # Example of thorough cleaning

def test_tool_usage_xml(webpage_reader_tool):
    usage_xml = webpage_reader_tool.tool_usage_xml()
    assert 'WebPageReader: Reads and cleans the HTML content from a given webpage.' in usage_xml
    assert '<command name="WebPageReader">' in usage_xml
    assert '<arg name="webpage_url">url_to_read</arg>' in usage_xml

def test_get_config_schema(webpage_reader_tool):
    schema = webpage_reader_tool.get_config_schema()
    assert schema is not None
    cleaning_mode_param = schema.get_parameter("cleaning_mode")
    assert cleaning_mode_param is not None
    assert cleaning_mode_param.name == "cleaning_mode"
    assert cleaning_mode_param.param_type == ParameterType.ENUM
    assert cleaning_mode_param.default_value == "THOROUGH"
    assert "BASIC" in cleaning_mode_param.enum_values
    assert "THOROUGH" in cleaning_mode_param.enum_values
