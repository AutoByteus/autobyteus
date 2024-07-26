import pytest
from unittest.mock import AsyncMock

from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker

@pytest.mark.asyncio
async def test_browser_session_aware_tools_integration():
    # Create instances of the tools
    webpage_reader = BrowserSessionAwareWebPageReader()
    element_trigger = BrowserSessionAwareWebElementTrigger()
    screenshot_taker = BrowserSessionAwareWebPageScreenshotTaker()



    # Define the test parameters
    root_url = "https://www.xiaohongshu.com/explore"
    element_selector = '.side-bar .channel-list li a[href="https://creator.xiaohongshu.com/publish/publish?source=official"]'
    screenshot_path = "/tmp/screenshot.png"

    # Step 1: Read the webpage content
    await webpage_reader.execute(url=root_url)

    # Step 2: Trigger a click event on the specified element
    await element_trigger.execute(element_locator=element_selector, event_type="click")

    # Step 3: Take a screenshot of the resulting page
    result_path = await screenshot_taker.execute(url=root_url, file_path=screenshot_path)
    assert result_path == screenshot_path