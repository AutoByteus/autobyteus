import pytest
from unittest.mock import AsyncMock, Mock # Added Mock

from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    # For session aware tools, the base class might try to access shared_browser_session_manager through context if designed that way.
    # For now, assuming agent_id is sufficient as per BaseTool.execute logic.
    # If SharedBrowserSessionManager is accessed via context, it would need mocking here too.
    # Based on current BrowserSessionAwareTool, it instantiates its own SharedBrowserSessionManager.
    return mock_context

@pytest.fixture
def element_trigger():
    return BrowserSessionAwareWebElementTrigger()

@pytest.fixture
def webpage_reader():
    # This reader is used for verification, so default init is fine
    return BrowserSessionAwareWebPageReader(content_cleanup_level=CleaningMode.STANDARD)

@pytest.mark.asyncio
async def test_browser_session_aware_element_trigger_execute_click(element_trigger, webpage_reader, mock_agent_context, tmp_path): # Added mock_agent_context, tmp_path for file saving
    # This test is more of an integration test as it interacts with external websites.
    # For robust unit tests, Playwright interactions should be mocked.
    # Given the existing structure, I'll adapt it.
    
    # Mock the shared_browser_session_manager and shared_session to avoid real browser interactions
    mock_shared_session = AsyncMock()
    mock_shared_session.page.locator.return_value.click = AsyncMock()
    mock_shared_session.page.content = AsyncMock(return_value="<html><body>Clicked Page Content</body></html>")

    mock_session_manager = Mock()
    mock_session_manager.get_shared_browser_session.return_value = mock_shared_session
    mock_session_manager.create_shared_browser_session = AsyncMock()

    element_trigger.shared_browser_session_manager = mock_session_manager
    webpage_reader.shared_browser_session_manager = mock_session_manager
    
    # Execute the trigger
    action_result = await element_trigger.execute(
        mock_agent_context, # Added mock_agent_context
        webpage_url="https://creator.xiaohongshu.com/publish/publish?source=official", 
        css_selector="div.tab:not(.active) span.title", 
        action="click"
    )
    assert action_result == "The WebElementTrigger command is executed"

    # Verify the action (simplified, as real verification needs page state)
    mock_shared_session.page.locator.assert_called_once_with("div.tab:not(.active) span.title")
    mock_shared_session.page.locator.return_value.click.assert_called_once()
    
    # Read the page content after action (using mocked session)
    page_content_after_click = await webpage_reader.execute(
        mock_agent_context, # Added mock_agent_context
        webpage_url="https://creator.xiaohongshu.com/publish/publish?source=official" # webpage_url needed for session creation if not existing
    )
    
    assert page_content_after_click == "Clicked Page Content" # Verifying cleaned mocked content

    # Save the page content to a file (optional, can be removed if not essential for test logic)
    file_name = tmp_path / "xioahongshu_trigger_test.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content_after_click)
    
    print(f"Page content saved to {file_name}")

def test_tool_usage_xml(element_trigger):
    usage_xml = element_trigger.tool_usage_xml()
    assert 'WebElementTrigger: Triggers actions on web elements on web pages' in usage_xml
    assert '<command name="WebElementTrigger">' in usage_xml
    assert '<arg name="webpage_url">url</arg>' in usage_xml
    assert '<arg name="css_selector">selector</arg>' in usage_xml
    assert '<arg name="action">action</arg>' in usage_xml
    assert 'click: No additional params required.' in usage_xml
    assert 'type: Requires \'text\' param.' in usage_xml
