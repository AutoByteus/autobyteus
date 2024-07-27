# File: tests/test_xiaohongshu_poster.py
import pytest
from autobyteus.tools.social_media_poster.xiaohongshu.xiaohongshu_poster import XiaohongshuPoster

@pytest.mark.asyncio
async def test_xiaohongshu_poster_english_book():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")

    # Test posting with English original title and Chinese translated title
    original_title = "The Great Gatsby"
    translated_title = "了不起的盖茨比"
    content = """
    《了不起的盖茨比》是一部经典的美国小说，作者是F. 斯科特·菲茨杰拉德。这本书通过描绘1920年代的美国社会，深刻揭示了"美国梦"的本质。
    故事围绕着神秘的百万富翁杰伊·盖茨比展开，他的奢华生活和神秘过去引人入胜。盖茨比对黛西·布坎南的执着追求，反映了他对理想生活的渴望。
    然而，小说最终揭示了这种理想的虚幻和空洞，通过盖茨比的悲剧命运，菲茨杰拉德批判了社会的腐败和道德的沦丧。
    这本书不仅是对那个时代的真实写照，更是对人性和社会的深刻反思。无论是语言的优美还是情节的紧凑，都让人难以忘怀。
    """
    result = await xiaohongshu_poster.execute(original_title=original_title, translated_title=translated_title, content=content)

    assert "published successfully on Xiaohongshu" in result

@pytest.mark.asyncio
async def test_xiaohongshu_poster_french_book():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")

    # Test posting with French original title and Chinese translated title
    original_title = "Le Petit Prince"
    translated_title = "小王子"
    content = """
    《小王子》是法国作家安托万·德·圣-埃克苏佩里创作的一部经典童话小说。这本书通过一个小男孩的冒险故事，传达了深刻的人生哲理。
    小王子离开他的小行星，开始了一段探索宇宙的旅程。他遇到了各种各样的人和事，每一次经历都让他更加理解生命的真谛。
    书中的玫瑰花象征着爱与责任，小王子与狐狸的对话则揭示了友谊的重要性。通过这些简单而深刻的故事，作者告诉我们要珍惜眼前的美好，保持纯真的心灵。
    《小王子》不仅适合孩子们阅读，也能给成年人带来深刻的启示。它提醒我们在忙碌的生活中，不要忘记心中的那份纯真与善良。
    """
    result = await xiaohongshu_poster.execute(original_title=original_title, translated_title=translated_title, content=content)

    assert "published successfully on Xiaohongshu" in result
    
@pytest.mark.asyncio
async def test_xiaohongshu_poster_chinese_book():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")
    
    # Test posting with Chinese original title (same as translated title)
    original_title = "红楼梦"
    translated_title = "红楼梦"
    content = """
    《红楼梦》是中国古典文学巅峰之作，由清代作家曹雪芹所著。这部小说以贾宝玉、林黛玉、薛宝钗等人的爱情故事为主线，
    深刻描绘了封建社会末期的人情世态。小说中充满了诗情画意，以细腻的笔触刻画了大观园中的日常生活，
    同时也揭示了封建家族的没落过程。《红楼梦》不仅是一部爱情小说，更是一部社会百科全书，
    其中蕴含的哲学思想、人生智慧至今仍给读者以深刻启示。
    """
    
    result = await xiaohongshu_poster.execute(original_title=original_title, translated_title=translated_title, content=content)
    
    assert "published successfully on Xiaohongshu" in result

@pytest.mark.asyncio
async def test_xiaohongshu_poster_error_handling():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")

    # Test with missing original title
    with pytest.raises(ValueError, match="'original_title' \(in any language\), 'translated_title' \(in Chinese\), and 'content' \(in Chinese\) are all required for the book review."):
        await xiaohongshu_poster.execute(translated_title="测试书评", content="测试内容")

    # Test with missing translated title
    with pytest.raises(ValueError, match="'original_title' \(in any language\), 'translated_title' \(in Chinese\), and 'content' \(in Chinese\) are all required for the book review."):
        await xiaohongshu_poster.execute(original_title="Test Book Review", content="测试内容")

    # Test with missing content
    with pytest.raises(ValueError, match="'original_title' \(in any language\), 'translated_title' \(in Chinese\), and 'content' \(in Chinese\) are all required for the book review."):
        await xiaohongshu_poster.execute(original_title="Test Book Review", translated_title="测试书评")

@pytest.mark.asyncio
async def test_xiaohongshu_poster_image_upload_timeout():
    xiaohongshu_poster = XiaohongshuPoster(xiaohongshu_account_name="TestAccount")
    
    # Test timeout scenario for image upload
    original_title = "1984"
    translated_title = "一九八四"
    content = "《一九八四》是一部令人不寒而栗的反乌托邦小说，其中描绘的极权社会至今仍具有现实意义。"
    
    # Mock the page.wait_for_selector method to simulate a timeout
    async def mock_wait_for_selector(*args, **kwargs):
        raise TimeoutError("Timed out waiting for selector")
    
    xiaohongshu_poster.page.wait_for_selector = mock_wait_for_selector
    
    with pytest.raises(Exception, match="An error occurred while creating the book review post on Xiaohongshu"):
        await xiaohongshu_poster.execute(original_title=original_title, translated_title=translated_title, content=content)