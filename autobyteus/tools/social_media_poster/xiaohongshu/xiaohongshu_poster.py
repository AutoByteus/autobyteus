import asyncio
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.tools.social_media_poster.xiaohongshu.repositories.xiaohongshu_book_review_repository import XiaohongshuBookReviewModel, XiaohongshuBookReviewRepository

class XiaohongshuPoster(BaseTool, UIIntegrator):
    def __init__(self, xiaohongshu_account_name):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        
        self.post_creation_url = 'https://creator.xiaohongshu.com/publish/publish?source=official'
        self.image_text_tab_selector = 'div.tab:not(.active) span.title'
        self.title_input_selector = '.input.titleInput input'
        self.content_input_selector = '#post-textarea'
        self.publish_button_selector = '.publishBtn'
        self.image_upload_finished_selector = 'div.btn.edit'
        self.xiaohongshu_account_name = xiaohongshu_account_name

    def tool_usage(self) -> str:
        return 'XiaohongshuPoster: Publishes a book review on Xiaohongshu. Usage: <<<XiaohongshuPoster(title="Book Review Title", content="Book review content")>>>'

    def tool_usage_xml(self) -> str:
        return '''XiaohongshuPoster: Publishes a book review on Xiaohongshu. Usage:
        <command name="XiaohongshuPoster">
        <arg name="title">Book Review Title</arg>
        <arg name="content">Book review content</arg>
        </command>
        where "title" is the title of the book review and "content" is the main text of the review.
        '''

    async def execute(self, **kwargs) -> str:
        book_review = XiaohongshuBookReviewModel(
            title=kwargs.get('title'),
            content=kwargs.get('content')
        )

        if not book_review.title or not book_review.content:
            raise ValueError("Both 'title' and 'content' are required for the book review.")

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

            # Input title
            await self.page.fill(self.title_input_selector, book_review.title)

            # Input content
            await self.page.fill(self.content_input_selector, book_review.content)

            # Click publish button
            publish_button = await self.page.wait_for_selector(self.publish_button_selector)
            await publish_button.click()

            # Wait for post to be published
            await self.wait_for_post_submission()

            # Save the posted book review to the database
            book_review_repository = XiaohongshuBookReviewRepository()
            book_review_repository.create(book_review)

            return f"Book review '{book_review.title}' published successfully on Xiaohongshu!"
        except Exception as e:
            return f"An error occurred while creating the book review post on Xiaohongshu: {str(e)}"
        finally:
            await asyncio.sleep(3)
            await self.close()


    async def wait_for_image_upload(self):
        try:
            # First, wait for the title input selector to appear
            await self.page.wait_for_selector(self.title_input_selector, state='visible', timeout=300000)  # 5-minute timeout
            print("Title input detected. Checking for image upload completion.")

            # Then, wait for the image upload finished indicator to appear
            await self.page.wait_for_selector(self.image_upload_finished_selector, state='hidden', timeout=30000)  # 30-second timeout
            print("Image upload detected. Proceeding with book review post creation.")
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