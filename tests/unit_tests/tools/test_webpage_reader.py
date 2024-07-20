import pytest
from autobyteus.tools.webpage_reader import WebPageReader

@pytest.mark.asyncio
async def test_webpage_reader():
    url = "https://docs.anthropic.com/en/docs/build-with-claude/tool-use"
    webpage_reader = WebPageReader()
    page_content = await webpage_reader.execute(url=url)
    
    # Save the page content to a file
    file_name = "claude_function_calling.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")
