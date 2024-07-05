import pytest
from autobyteus.tools.webpage_source_extractor import WebPageSourceExtractor

@pytest.mark.asyncio
async def test_webpage_source_extractor():
    url = "https://en.wikipedia.org/wiki/Forrest_Gump"
    webpage_source_extractor = WebPageSourceExtractor()
    page_content = await webpage_source_extractor.execute(url=url)
    
    assert "Forrest Gump" in page_content
    assert "</html>" in page_content