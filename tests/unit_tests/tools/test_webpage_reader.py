import pytest
from autobyteus.tools.webpage_reader import WebPageReader

@pytest.mark.asyncio
async def test_webpage_reader():
    url = "https://www.xiaohongshu.com/explore"
    webpage_reader = WebPageReader()
    page_content = await webpage_reader.execute(url=url)
    
    # Save the page content to a file
    file_name = "xiaohongshu.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")
