# File: autobyteus/tools/pdf_downloader.py

import os
import requests
import logging
from datetime import datetime
from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.file_utils import get_default_download_folder

class PDFDownloader(BaseTool):
    """
    A tool that downloads a PDF file from a given URL and saves it locally.
    """

    def __init__(self, custom_download_folder=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.default_download_folder = get_default_download_folder()
        self.download_folder = custom_download_folder or self.default_download_folder

    def tool_usage(self):
        """
        Return a string describing the usage of the PDFDownloader tool.
        """
        return 'PDFDownloader: Downloads a PDF file from a given URL. Usage: <<<PDFDownloader(url="https://example.com/file.pdf")>>>'

    def tool_usage_xml(self):
        return '''PDFDownloader: Downloads a PDF file from a given URL. Usage:
    <command name="PDFDownloader">
    <arg name="url">https://example.com/file.pdf</arg>
    </command>
    '''

    def _execute(self, **kwargs):
        """
        Download a PDF file from the given URL and save it locally.

        Args:
            **kwargs: Keyword arguments containing the URL.
                      'url': The URL of the PDF file to download.
                      'folder' (optional): Custom download folder path.

        Returns:
            str: A message indicating the result of the download operation.

        Raises:
            ValueError: If the 'url' keyword argument is not specified.
        """
        url = kwargs.get('url')
        custom_folder = kwargs.get('folder')
        download_folder = custom_folder or self.download_folder

        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        self.logger.info(f"Attempting to download PDF from {url}")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raises an HTTPError for bad responses

            # Check if the content type is PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' not in content_type:
                raise ValueError(f"The URL does not point to a PDF file. Content-Type: {content_type}")

            # Generate a unique filename based on the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"downloaded_pdf_{timestamp}.pdf"
            save_path = os.path.join(download_folder, filename)

            # Ensure the directory exists
            os.makedirs(download_folder, exist_ok=True)

            # Save the PDF file
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            self.logger.info(f"PDF successfully downloaded and saved to {save_path}")
            return f"PDF successfully downloaded and saved to {save_path}"

        except requests.exceptions.RequestException as e:
            error_message = f"Error downloading PDF: {str(e)}"
            self.logger.error(error_message)
            return error_message
        except ValueError as e:
            error_message = str(e)
            self.logger.error(error_message)
            return error_message
        except IOError as e:
            error_message = f"Error saving PDF: {str(e)}"
            self.logger.error(error_message)
            return error_message