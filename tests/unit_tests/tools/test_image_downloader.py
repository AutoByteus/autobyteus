import os
import asyncio
import pytest
from autobyteus.tools.image_downloader import ImageDownloader

@pytest.mark.asyncio
async def test_execute_success():
    downloader = ImageDownloader()
    url = 'https://cdn.cookielaw.org/logos/static/ot_company_logo.png'  # Replace with a real image URL for testing
    
    
    await downloader.execute(url=url)

