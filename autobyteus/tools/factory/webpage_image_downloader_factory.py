from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_image_downloader import WebPageImageDownloader

class WebPageImageDownloaderFactory(ToolFactory):
    def create_tool(self) -> WebPageImageDownloader:
        return WebPageImageDownloader()