import pytest
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

@pytest.mark.asyncio
async def test_webpage_reader():
    url = "https://pubmed.ncbi.nlm.nih.gov/34561271/"
    webpage_reader = WebPageReader(content_cleanup_level=CleaningMode.STANDARD)
    page_content = await webpage_reader.execute(url=url)
    
    # Save the page content to a file
    file_name = "paper_details.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(page_content)
    
    print(f"Page content saved to {file_name}")
