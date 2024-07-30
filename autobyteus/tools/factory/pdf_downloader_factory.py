from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.pdf_downloader import PDFDownloader

class PDFDownloaderFactory(ToolFactory):
    def __init__(self, custom_download_folder: str = None):
        self.custom_download_folder = custom_download_folder

    def create_tool(self) -> PDFDownloader:
        return PDFDownloader(custom_download_folder=self.custom_download_folder)