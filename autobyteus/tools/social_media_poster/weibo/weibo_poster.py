import asyncio
import os
from typing import Optional
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.tools.social_media_poster.weibo.image_uploader import ImageUploader
from autobyteus.tools.social_media_poster.weibo.repositories.reviewed_movie_repository import ReviewedMovieModel, ReviewedMovieRepository
from autobyteus.tools.social_media_poster.weibo.screenshot import capture_screenshot, save_screenshot
from autobyteus.tools.social_media_poster.weibo.window_utils import find_window_by_name

class WeiboPoster(BaseTool, UIIntegrator):
    """
    A tool that allows for publishing a post on Weibo using Playwright.

    This class inherits from BaseTool and UIIntegrator. Upon initialization via the UIIntegrator's
    initialize method, self.page becomes available as a Playwright page object for interaction
    with the web browser.
    """

    def __init__(self, weibo_account_name):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        
        self.post_content_selector = 'textarea.Form_input_2gtXx'
        self.image_upload_button_selector = 'div.VPlus_itemin_309nn.VPlus_file_n7Xjc'
        self.file_input_selector = 'input[type="file"].FileUpload_file_27ilM'
        self.submit_button_selector = 'button span.woo-button-content:has-text("发送")'
        self.uploaded_image_close_icon_selector = 'i.Image_close_3Ikpk[title="删除"]'
        self.uploaded_image_selector = 'div.Image_focus_23gKL'

        self.weibo_account_name = weibo_account_name


    def tool_usage(self) -> str:
        return 'WeiboPoster: Publishes a movie review post on Weibo. Usage: <<<WeiboPoster(movie_title="movie title", content="review content", image_path="/full/path/to/image.jpg")>>>, where "movie_title" is a string representing the title of the movie being reviewed, "review content" is a string containing the review text, and "image_path" is an optional full file path to an image.'

    def tool_usage_xml(self) -> str:
        return '''WeiboPoster: Publishes a movie review post on Weibo. Usage:
        <command name="WeiboPoster">
        <arg name="movie_title"> original movie title (if originally in English, use the English title)</arg>
        <arg name="content">review content</arg>
        <arg name="image_path">/full/path/to/image.jpg</arg>
        </command>
        where "movie_title" is a string representing the title of the movie being reviewed, "review content" is a string containing the review text which is written in Chinese, and "image_path" is an optional full file path to an image.
        '''
    
    async def wait_for_image_upload(self):
        await self.page.wait_for_selector(self.uploaded_image_selector, timeout=10000)


    async def wait_for_file_chooser_dialog(self, timeout=10):
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            dialog_window = find_window_by_name("Dateien öffnen")
            if dialog_window:
                return True
            await asyncio.sleep(1)
        return False
    
    async def wait_for_post_submission(self):
        feed_body_selector = 'div.Feed_body_3R0rO'
        account_name_link_selector = f'a[aria-label="{self.weibo_account_name}"]'
        await self.page.wait_for_selector(f'{feed_body_selector} {account_name_link_selector}', timeout=10000)
        print("published successfully")

    async def execute(self, **kwargs) -> str:
        """
        Publish a movie review post on Weibo using Playwright.

        This method initializes the Playwright browser, navigates to Weibo, creates a post with the given
        movie title and review content, optionally uploads an image, and submits the post. The reviewed movie
        is then saved to the database using the ReviewedMovieRepository.

        Args:
            **kwargs: Keyword arguments containing the movie title, review content, and optional image path.
                    'movie_title': The title of the movie being reviewed (required).
                    'content': The text content of the review (required).
                    'image_path': The full file path to an image to be uploaded (optional).

        Returns:
            str: A string containing a success message or error information.

        Raises:
            ValueError: If the 'movie_title' or 'content' keyword argument is not specified,
                        or if the 'image_path' is provided but is not a full path or the file does not exist.
        """
        movie_title: str = kwargs.get('movie_title')
        content: str = kwargs.get('content')
        image_path: Optional[str] = kwargs.get('image_path')

        if not movie_title:
            raise ValueError("The 'movie_title' keyword argument must be specified.")
        if not content:
            raise ValueError("The 'content' keyword argument must be specified.")

        if image_path:
            if not os.path.isabs(image_path):
                raise ValueError("The 'image_path' must be a full path.")
            if not os.path.exists(image_path):
                raise ValueError(f"The image file does not exist at the specified path: {image_path}")


        if image_path:
            if not os.path.isabs(image_path):
                raise ValueError("The 'image_path' must be a full path.")
            if not os.path.exists(image_path):
                raise ValueError(f"The image file does not exist at the specified path: {image_path}")

        # Call the initialize method from the UIIntegrator class to set up the Playwright browser
        await self.initialize()

        try:
            # Navigate to Weibo
            await self.page.goto('https://www.weibo.com/')
            await self.page.wait_for_load_state('networkidle')

            # Input post content
            await self.page.fill(self.post_content_selector, content)

            # Upload image if provided
            if image_path:
                await self.page.click(self.image_upload_button_selector)
                # Wait for the file chooser dialog to appear
                dialog_appeared = await self.wait_for_file_chooser_dialog()
                if not dialog_appeared:
                    raise Exception("File chooser dialog did not appear within the timeout.")

                # Capture screenshot
                screenshot = capture_screenshot()
                save_screenshot(screenshot, "weibo_screenshot.png")

                image_uploader = ImageUploader()
                await image_uploader.locate_and_click_downloads_folder(screenshot)
                await image_uploader.locate_and_upload_image(screenshot)

                # Wait for the file input selector to be visible
                # await self.page.wait_for_selector(self.uploaded_image_close_icon_selector, state='visible', timeout=10000)
                # await self.page.wait_for_load_state("networkidle")
                await self.wait_for_image_upload()

            submit_button = await self.page.wait_for_selector(self.submit_button_selector)
            await submit_button.click()

            # Wait for the post to be published
            await self.wait_for_post_submission()


            # Save the reviewed movie to the database
            movie_review_repository = ReviewedMovieRepository()
            reviewed_movie = ReviewedMovieModel(movie_title=movie_title, content=content)
            movie_review_repository.create(reviewed_movie)

            return "Post created successfully!"
        except Exception as e:
            return f"An error occurred while creating the post: {str(e)}"

        finally:
            await asyncio.sleep(3)
            await self.close()