import os
import pytest
from autobyteus.tools.webpage_image_downloader import WebPageImageDownloader

@pytest.mark.asyncio
async def test_webpage_image_downloader():
    url = "https://www.kaufland.de/"  # Replace with a real URL for testing
    save_dir = "kaufland"

    downloader = WebPageImageDownloader()
    saved_paths = await downloader.execute(url=url, save_dir=save_dir)

    assert len(saved_paths) > 0, "No images were downloaded"

    for path in saved_paths:
        assert os.path.exists(path), f"Downloaded image not found at {path}"
        assert path.startswith(save_dir), f"Image not saved in specified directory: {path}"
        assert os.path.splitext(path)[1] in ['.png', '.jpg', '.jpeg', '.gif'], f"Unexpected image format: {path}"