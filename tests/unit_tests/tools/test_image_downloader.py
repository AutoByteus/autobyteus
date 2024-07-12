import os
import asyncio
import pytest
from autobyteus.tools.image_downloader import ImageDownloader

@pytest.mark.asyncio
async def test_execute_success():
    downloader = ImageDownloader()
    url = 'https://cdn.cookielaw.org/logos/static/ot_company_logo.png'  # Replace with a real image URL for testing
    
    
    filepath = await downloader.execute(url=url)

    assert filepath.startswith('downloads/downloaded_image_')
    assert filepath.endswith('.png')
    assert os.path.isfile(filepath)

    # Clean up the downloaded file
    os.remove(filepath)

