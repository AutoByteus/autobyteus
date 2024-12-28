from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator
import os
from urllib.parse import urljoin

class WebPageImageDownloader(BaseTool, UIIntegrator):
    """
    A class that downloads images (excluding SVGs) from a given webpage using Playwright.
    """
    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

    def tool_usage(self):
        return "WebPageImageDownloader: Downloads images (excluding SVGs) from a given webpage and saves them to the specified directory. Usage: <<<WebPageImageDownloader(url='webpage_url', save_dir='path/to/save/directory')>>>, where 'webpage_url' is a string containing the URL of the webpage to download images from, and 'path/to/save/directory' is the directory where the images will be saved."

    def tool_usage_xml(self):
            return '''
    WebPageImageDownloader: Downloads images (excluding SVGs) from a given webpage and saves them to the specified directory. Usage:
    <command name="WebPageImageDownloader">
    <arg name="url">webpage_url</arg>
    <arg name="save_dir">path/to/save/directory</arg>
    </command>
    where "webpage_url" is a string containing the URL of the webpage to download images from, and "path/to/save/directory" is the directory where the images will be saved.
    '''

    async def _execute(self, **kwargs):
        """
        Download images (excluding SVGs) from the webpage at the given URL using Playwright and save them to the specified directory.

        Args:
            **kwargs: Keyword arguments containing the URL and save directory. The URL should be specified as 'url', and the directory as 'save_dir'.

        Returns:
            list: The file paths of the saved images.

        Raises:
            ValueError: If the 'url' or 'save_dir' keyword arguments are not specified.
        """
        url = kwargs.get('url')
        save_dir = kwargs.get('save_dir')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")
        if not save_dir:
            raise ValueError("The 'save_dir' keyword argument must be specified.")
        
        os.makedirs(save_dir, exist_ok=True)

        await self.initialize()
        await self.page.goto(url, wait_until="networkidle")
        
        image_urls = await self._get_image_urls()
        
        saved_paths = []
        for i, image_url in enumerate(image_urls):
            full_url = self._resolve_url(url, image_url)
            if not self._is_svg(full_url):
                file_path = self._generate_file_path(save_dir, i, full_url)
                await self._download_and_save_image(full_url, file_path)
                saved_paths.append(file_path)
        
        return saved_paths

    async def _get_image_urls(self):
        """
        Get the URLs of all images on the current page.

        Returns:
            list: A list of image URLs.
        """
        image_urls = await self.page.evaluate("""() => {
            return Array.from(document.images).map(i => i.src);
        }""")
        return image_urls
    
    def _resolve_url(self, base_url, url):
        """
        Resolve a URL against a base URL to get the absolute URL.

        Args:
            base_url (str): The base URL.
            url (str): The URL to resolve.

        Returns:
            str: The absolute URL.
        """
        return urljoin(base_url, url)

    def _is_svg(self, url):
        """
        Check if a URL points to an SVG image.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL points to an SVG, False otherwise.
        """
        return url.lower().endswith('.svg')

    def _generate_file_path(self, directory, index, url):
        """
        Generate a unique file path for an image.

        Args:
            directory (str): The directory to save the image in.
            index (int): A unique index for this image.
            url (str): The URL of the image (used to get the file extension).

        Returns:
            str: The generated file path.
        """
        ext = os.path.splitext(url)[1]
        filename = f"image_{index}{ext}"
        return os.path.join(directory, filename)

    async def _download_and_save_image(self, url, file_path):
        """
        Download an image from a URL and save it to a file.

        Args:
            url (str): The URL of the image to download.
            file_path (str): The path to save the image to.
        """
        await self.page.goto(url)
        image_buffer = await self.page.screenshot(full_page=True)
        with open(file_path, "wb") as f:
            f.write(image_buffer)