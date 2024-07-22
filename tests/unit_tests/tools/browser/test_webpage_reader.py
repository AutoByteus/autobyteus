import pytest
from autobyteus.tools.browser.webpage_reader import WebPageReader

@pytest.mark.asyncio
async def test_webpage_reader():
    url = "https://pinia.vuejs.org/ssr/nuxt.html"
    webpage_reader = WebPageReader()
    page_content = await webpage_reader.execute(url=url)
    
    # Save the page content to a file
    file_name = "pinia_store.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")
