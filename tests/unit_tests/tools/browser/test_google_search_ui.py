import pytest
from autobyteus.tools.browser.google_search_ui import GoogleSearch

@pytest.mark.asyncio
async def test_google_search():
    search_query = "The Shawshank Redemption movie poster"
    google_search = GoogleSearch()
    print(google_search.tool_usage())
    search_results = await google_search.execute(query=search_query)
    
       # Save the page content to a file
    file_name = "shawshank.html"
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(search_results)
