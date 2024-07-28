# File: autobyteus/tools/social_media_poster/xiaohongshu/xiaohongshu_poster.py

import asyncio
import pyperclip
import sys
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.tools.social_media_poster.xiaohongshu.repositories.book_review_repository import XiaohongshuBookReviewModel, ReviewedBooksRepository
from bson import ObjectId
from datetime import datetime

class XiaohongshuPoster(BaseTool, UIIntegrator):
    def __init__(self, xiaohongshu_account_name):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        
        self.post_creation_url = 'https://creator.xiaohongshu.com/publish/publish?source=official'
        self.image_text_tab_selector = 'div.tab:not(.active) span.title'
        self.title_input_selector = '.input.titleInput input'
        self.content_input_selector = '#post-textarea'
        self.publish_button_selector = '.publishBtn'
        self.uploading_indicator = '.img-container .mask.uploading'
        self.xiaohongshu_account_name = xiaohongshu_account_name

    def tool_usage(self) -> str:
        usage = (
            "XiaohongshuPoster: Publishes a book review on Xiaohongshu (小红书). "
            "This tool allows you to create engaging book review posts with both original title (in any language) and Chinese translated title. "
            "Note: The translated_title must be within 20 words and will be used as the post title.\n"
            "Usage: <<<XiaohongshuPoster(original_title=\"Original Title\", translated_title=\"中文标题 (20 words max)\", content=\"Book review content in Chinese\")>>>\n\n"
            "Examples:\n"
            "1. English book:\n"
            "<<<XiaohongshuPoster(\n"
            "    original_title=\"To Live\",\n"
            "    translated_title=\"活着\",\n"
            "    content=\"余华的《活着》是一部震撼人心的小说，讲述了一个普通中国家庭在动荡年代的生存故事。...\"\n"
            ")>>>\n\n"
            "2. French book:\n"
            "<<<XiaohongshuPoster(\n"
            "    original_title=\"Le Petit Prince\",\n"
            "    translated_title=\"小王子\",\n"
            "    content=\"《小王子》是一部充满哲理的童话故事，讲述了一个来自外星球的小王子的奇妙冒险...\"\n"
            ")>>>\n\n"
            "3. INCORRECT EXAMPLE - DO NOT USE:\n"
            "<<<XiaohongshuPoster(\n"
            "    original_title=\"The Catcher in the Rye\",\n"
            "    translated_title=\"麦田里的守望者：一部探讨青春期叛逆与成长的经典小说，深刻剖析了现代社会中年轻人的困惑与迷茫\",\n"
            "    content=\"...\"\n"
            ")>>>\n"
            "THIS IS ABSOLUTELY WRONG! The translated_title is way over the 20-word limit. "
            "Such long titles are strictly prohibited and will cause the post to fail. "
            "Always keep your translated titles concise and within the 20-word limit!"
        )
        return usage

    def tool_usage_xml(self) -> str:
        usage = '''XiaohongshuPoster: Publishes a book review on Xiaohongshu (小红书). This tool creates engaging book review posts with both original title (in any language) and Chinese translated title. Note: The translated_title must be within 20 words and will be used as the post title. Usage:
        <command name="XiaohongshuPoster">
            <arg name="original_title">Original Title (in any language)</arg>
            <arg name="translated_title">中文标题 (20 words max)</arg>
            <arg name="content">Book review content in Chinese</arg>
        </command>
        where "original_title" is the book's title in its original language, "translated_title" is the Chinese translation of the title (max 20 words) and will be used as the post title, and "content" is the main text of the review in Chinese.

        Examples:
        1. English book:
        <command name="XiaohongshuPoster">
            <arg name="original_title">To Live</arg>
            <arg name="translated_title">活着</arg>
            <arg name="content">余华的《活着》是一部震撼人心的小说，讲述了一个普通中国家庭在动荡年代的生存故事。...</arg>
        </command>

        2. French book:
        <command name="XiaohongshuPoster">
            <arg name="original_title">Le Petit Prince</arg>
            <arg name="translated_title">小王子</arg>
            <arg name="content">《小王子》是一部充满哲理的童话故事，讲述了一个来自外星球的小王子的奇妙冒险...</arg>
        </command>

        3. INCORRECT EXAMPLE - DO NOT USE:
        <command name="XiaohongshuPoster">
            <arg name="original_title">The Catcher in the Rye</arg>
            <arg name="translated_title">麦田里的守望者：一部探讨青春期叛逆与成长的经典小说，深刻剖析了现代社会中年轻人的困惑与迷茫</arg>
            <arg name="content">...</arg>
        </command>
        THIS IS ABSOLUTELY WRONG! The translated_title is way over the 20-word limit. 
        Such long titles are strictly prohibited and will cause the post to fail. 
        Always keep your translated titles concise and within the 20-word limit!
        '''
        return usage

    async def _execute(self, **kwargs) -> str:
        original_title = kwargs.get('original_title')
        translated_title = kwargs.get('translated_title')
        content = kwargs.get('content')

        if not original_title or not translated_title or not content:
            raise ValueError("'original_title', 'translated_title', and 'content' are all required for the book review.")

        if len(translated_title.split()) > 20:
            raise ValueError("The translated_title must be within 20 words.")

        book_review = XiaohongshuBookReviewModel(
            review_id=ObjectId(),
            original_title=original_title,
            title=translated_title,  # Use translated_title as the post title
            content=content,
            timestamp=datetime.utcnow()
        )

        await self.initialize()

        try:
            # Navigate directly to the post creation page
            await self.page.goto(self.post_creation_url)
            await self.page.wait_for_load_state('networkidle')

            # Click the "Image & Text" tab
            image_text_tab = await self.page.wait_for_selector(self.image_text_tab_selector)
            await image_text_tab.click()

            # Prompt user to upload image
            print("Please upload an image for your Xiaohongshu book review post.")

            # Wait for the image upload to finish
            await self.wait_for_image_upload()
            await asyncio.sleep(1)

            # Input translated title as the post title
            await self._copy_paste_text(self.title_input_selector, book_review.title)

            # Input content
            await self._copy_paste_text(self.content_input_selector, book_review.content)

            # Click publish button
            publish_button = await self.page.wait_for_selector(self.publish_button_selector)
            await publish_button.click()

            # Wait for post to be published
            await self.wait_for_post_submission()

            # Save the posted book review to the database
            book_review_repository = ReviewedBooksRepository()
            book_review_repository.create(book_review)

            return f"Book review '{book_review.title}' published successfully on Xiaohongshu!"
        except Exception as e:
            return f"An error occurred while creating the book review post on Xiaohongshu: {str(e)}"
        finally:
            await asyncio.sleep(3)
            await self.close()

    async def _copy_paste_text(self, selector: str, text: str) -> None:
        """
        Copy the text to the clipboard and paste it into the specified element.
        """
        pyperclip.copy(text)
        await self.page.focus(selector)
        
        # Determine the appropriate paste shortcut based on the operating system
        paste_shortcut = "Meta+V" if sys.platform == "darwin" else "Control+V"
        
        await self.page.keyboard.press(paste_shortcut)  # Paste from clipboard
        await asyncio.sleep(0.5)  # Short delay to ensure the paste operation completes

    async def wait_for_image_upload(self):
        try:
            uploading_indicator = self.page.locator(self.uploading_indicator)
            # Wait for the uploading indicator to appear (in case it's not immediately present)
            await uploading_indicator.wait_for(state='attached', timeout=0)
            
            # Wait for the uploading indicator to disappear
            await uploading_indicator.wait_for(state='detached', timeout=0)
            await asyncio.sleep(1)
            print("Image upload completed successfully.")

        except Exception as e:
            raise Exception(f"Error while waiting for image upload: {str(e)}")

    async def wait_for_post_submission(self):
        try:
            # Wait for the success container to appear
            await self.page.wait_for_selector('.success-container', state='visible', timeout=30000)
            
            # Verify that the success message is present
            success_title = await self.page.query_selector('.success-container .content .title')
            success_text = await success_title.inner_text()
            
            if success_text.strip() == "发布成功":
                print("Post published successfully on Xiaohongshu!")
            else:
                raise Exception("Unexpected content in success message")
        except Exception as e:
            raise Exception(f"Error while waiting for post submission: {str(e)}")