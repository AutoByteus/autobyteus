import pytest
from unittest.mock import AsyncMock

from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader

@pytest.mark.asyncio
async def test_browser_session_aware_webpage_reader_execute():
    webpage_reader = BrowserSessionAwareWebPageReader()

    await webpage_reader.execute(url="https://www.xiaohongshu.com/explore")

