# file: autobyteus/tests/unit_tests/tools/test_web_page_reader.py
import pytest
from autobyteus.tools.web_page_reader import WebPageReader

@pytest.mark.asyncio
async def test_web_page_reader():
    url = "https://en.wikipedia.org/wiki/Forrest_Gump"
    web_page_reader = WebPageReader()
    page_content = await web_page_reader.execute(url=url)
    
    print("Page Content:")
    print(page_content)