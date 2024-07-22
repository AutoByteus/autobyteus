import pytest
from unittest.mock import AsyncMock

from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker

@pytest.mark.asyncio
async def test_browser_session_aware_webpage_screenshot_taker_execute():
    screenshot_taker = BrowserSessionAwareWebPageScreenshotTaker()

    file_path = "/tmp/screenshot.png"
    result = await screenshot_taker.execute(url="https://www.xiaohongshu.com/explore", file_path=file_path)

    assert result == file_path
