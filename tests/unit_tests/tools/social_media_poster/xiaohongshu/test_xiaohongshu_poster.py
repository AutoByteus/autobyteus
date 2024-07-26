import pytest
import os
from autobyteus.tools.social_media_poster.xiaohongshu.xiaohongshu_poster import XiaohongshuPoster

@pytest.mark.asyncio
async def test_xiaohongshu_poster_text_only():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")
    
    # Test posting only text
    title = "The Great Gatsby"
    content = "A classic novel that captures the essence of the American Dream."
    result = await xiaohongshu_poster.execute(title=title, content=content)
    
    assert "published successfully on Xiaohongshu" in result

@pytest.mark.asyncio
async def test_xiaohongshu_poster_with_image_prompt():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")
    
    # Test posting text with an image prompt
    title = "Review: To Kill a Mockingbird"
    content = "A powerful exploration of racial injustice in the American South."
    
    result = await xiaohongshu_poster.execute(title=title, content=content)
    
    assert "published successfully on Xiaohongshu" in result

@pytest.mark.asyncio
async def test_xiaohongshu_poster_error_handling():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")

    # Test with missing title
    with pytest.raises(ValueError, match="Both 'title' and 'content' are required for the book review."):
        await xiaohongshu_poster.execute(content="Test review")

    # Test with missing content
    with pytest.raises(ValueError, match="Both 'title' and 'content' are required for the book review."):
        await xiaohongshu_poster.execute(title="Test Book Review")

@pytest.mark.asyncio
async def test_xiaohongshu_poster_image_upload_timeout():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")
    
    # Test timeout scenario for image upload
    title = "Review: 1984"
    content = "A chilling dystopian novel that remains relevant today."
    
    # Mock the page.wait_for_selector method to simulate a timeout
    async def mock_wait_for_selector(*args, **kwargs):
        raise TimeoutError("Timed out waiting for selector")
    
    xiaohongshu_poster.page.wait_for_selector = mock_wait_for_selector
    
    with pytest.raises(Exception, match="An error occurred while creating the book review post on Xiaohongshu"):
        await xiaohongshu_poster.execute(title=title, content=content)