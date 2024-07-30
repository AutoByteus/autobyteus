from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.image_downloader import ImageDownloader

class ImageDownloaderFactory(ToolFactory):
    def __init__(self, custom_download_folder: str = None):
        self.custom_download_folder = custom_download_folder

    def create_tool(self) -> ImageDownloader:
        return ImageDownloader(custom_download_folder=self.custom_download_folder)