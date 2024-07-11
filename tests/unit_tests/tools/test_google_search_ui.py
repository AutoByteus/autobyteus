import pytest
from autobyteus.tools.google_search_ui import GoogleSearch

@pytest.mark.asyncio
async def test_google_search():
    search_query = "Forrest Gump movie summary themes and reception"
    google_search = GoogleSearch()
    print(google_search.tool_usage())
    search_results = await google_search.execute(query=search_query)
    print(search_results)