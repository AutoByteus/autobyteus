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

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the WebPageImageDownloader tool.

        Returns:
            str: An XML description of how to use the WebPageImageDownloader tool.
        """
        return '''
    WebPageImageDownloader: Downloads images (excluding SVGs) from a given webpage and saves them to the specified directory. Usage:
    <command name="WebPageImageDownloader">
    <arg name="url">webpage_url</arg>
    <arg name="save_dir">path/to/save/directory</arg>
    </command>
    where "webpage_url" is a string containing the URL of the webpage to download images from, and "path/to/save/directory" is the directory where the images will be saved.
    '''

    async def _execute(self, **kwargs):
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
        image_urls = await self.page.evaluate("""() => {
            return Array.from(document.images).map(i => i.src);
        }""")
        return image_urls
    
    def _resolve_url(self, base_url, url):
        return urljoin(base_url, url)

    def _is_svg(self, url):
        return url.lower().endswith('.svg')

    def _generate_file_path(self, directory, index, url):
        ext = os.path.splitext(url)[1]
        filename = f"image_{index}{ext}"
        return os.path.join(directory, filename)

    async def _download_and_save_image(self, url, file_path):
        await self.page.goto(url)
        image_buffer = await self.page.screenshot(full_page=True)
        with open(file_path, "wb") as f:
            f.write(image_buffer)
