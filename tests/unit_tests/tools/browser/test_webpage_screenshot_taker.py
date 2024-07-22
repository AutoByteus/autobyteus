import pytest
import os
from autobyteus.tools.browser.webpage_screenshot_taker import WebPageScreenshotTaker

@pytest.mark.asyncio
async def test_webpage_screenshot_taker():
    url = "https://gemini.google.com/app/f851361aa822cfb8"
    file_path = "gemini.png"
    webpage_screenshot_taker = WebPageScreenshotTaker()
    saved_file_path = await webpage_screenshot_taker.execute(url=url, file_path=file_path)
    
    assert saved_file_path == file_path
    assert os.path.isfile(file_path)
