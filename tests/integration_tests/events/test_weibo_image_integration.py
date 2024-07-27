# File: autobyteus/tests/integration_tests/events/test_weibo_image_integration.py

import pytest
from autobyteus.tools.social_media_poster.weibo.weibo_poster import WeiboPoster
from autobyteus.tools.image_downloader import ImageDownloader

@pytest.mark.asyncio
async def test_weibo_post_image_deletion():
    weibo_poster = WeiboPoster(weibo_account_name="Normy-光影旅程")
    image_downloader = ImageDownloader()

    # Simulate downloading an image
    image_downloader.last_downloaded_image = "/home/ryan-ai/Downloads/downloaded_image_20240727_101028.jpg"

    # Execute WeiboPoster
    await weibo_poster.execute(movie_title="Test Movie", content="Test content")

    # Check if the image was "deleted"
    assert image_downloader.last_downloaded_image is None