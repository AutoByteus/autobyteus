import asyncio

from autobyteus.tools.social_media_poster.weibo.weibo_poster import WeiboPoster

async def test_weibo_poster_text_with_image():
    weibo_poster = WeiboPoster(weibo_account_name="RyanZhengHaliluya")
    
    # Test posting text with an image
    content_with_image = "This is a test post with an image from an automated integration test. Please ignore."
    image_path = "/home/ryan-ai/Downloads/weibo.jpeg"  # Replace with an actual image path on your system
    
    result_with_image = await weibo_poster.execute(content=content_with_image, image_path=image_path)
    print("Result:", result_with_image)

def main():
    asyncio.run(test_weibo_poster_text_with_image())

if __name__ == "__main__":
    main()
