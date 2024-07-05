import pytest
import os
from autobyteus.tools.webpage_screenshot_taker import WebPageScreenshotTaker

@pytest.mark.asyncio
async def test_webpage_screenshot_taker():
    url = "https://en.wikipedia.org/wiki/Forrest_Gump"
    file_path = "test_screenshot.pdf"
    webpage_screenshot_taker = WebPageScreenshotTaker()
    saved_file_path = await webpage_screenshot_taker.execute(url=url, file_path=file_path)
    
    assert saved_file_path == file_path
    assert os.path.isfile(file_path)
