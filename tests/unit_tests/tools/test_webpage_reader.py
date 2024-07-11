import pytest
from autobyteus.tools.webpage_reader import WebPageReader

@pytest.mark.asyncio
async def test_webpage_reader():
    url = "https://en.wikipedia.org/wiki/Forrest_Gump"
    webpage_reader = WebPageReader()
    page_content = await webpage_reader.execute(url=url)
    
    assert "Forrest Gump" in page_content
    assert "</html>" in page_content