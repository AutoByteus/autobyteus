import pytest
from unittest.mock import AsyncMock

from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
from autobyteus.tools.browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

@pytest.mark.asyncio
async def test_browser_session_aware_element_trigger_execute_click():
    element_trigger = BrowserSessionAwareWebElementTrigger()
    

    await element_trigger.execute(webpage_url="https://creator.xiaohongshu.com/publish/publish?source=official", css_selector="div.tab:not(.active) span.title", action="click")


    webpage_reader = BrowserSessionAwareWebPageReader(content_cleanup_level=CleaningMode.STANDARD)
    page_content = await webpage_reader.execute(webpage_url="https://creator.xiaohongshu.com/publish/publish?source=official")
    

    # Save the page content to a file
    file_name = "xioahongshu.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")


