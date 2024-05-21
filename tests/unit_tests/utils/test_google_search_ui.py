import pytest
from autobyteus.tools.google_search_ui import GoogleSearch

@pytest.mark.asyncio
async def test_execute_valid_query():
    google_search = GoogleSearch()
    query = "Encouraging story about students"

    result = await google_search.execute(query=query)

    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_execute_no_results():
    google_search = GoogleSearch()
    query = "asdfjkl;asdfjkl;asdfjkl;asdfjkl;asdfjkl"

    result = await google_search.execute(query=query)

    assert isinstance(result, str)
    assert len(result) == 0
