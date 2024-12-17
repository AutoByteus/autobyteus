from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator
import os
import logging

class WebPagePDFGenerator(BaseTool, UIIntegrator):
    """
    A class that generates a PDF of a given webpage using Playwright.
    """
    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        self.logger = logging.getLogger(__name__)

    def tool_usage(self):
        return "WebPagePDFGenerator: Generates a PDF of a given webpage in A4 format and saves it to the specified directory. Usage: <<<WebPagePDFGenerator(url='webpage_url', save_dir='path/to/save/directory')>>>, where 'webpage_url' is a string containing the URL of the webpage to generate a PDF from, and 'path/to/save/directory' is the directory where the PDF will be saved."

    def tool_usage_xml(self):
        return '''
        WebPagePDFGenerator: Generates a PDF of a given webpage in A4 format and saves it to the specified directory. Usage:
        <command name="WebPagePDFGenerator">
        <arg name="url">webpage_url</arg>
        <arg name="save_dir">path/to/save/directory</arg>
        </command>
        where "webpage_url" is a string containing the URL of the webpage to generate a PDF from, and "path/to/save/directory" is the directory where the PDF will be saved.
        '''

    async def _execute(self, **kwargs):
        """
        Generate a PDF of the webpage at the given URL using Playwright and save it to the specified directory.

        Args:
            **kwargs: Keyword arguments containing the URL and save directory. The URL should be specified as 'url', and the directory as 'save_dir'.

        Returns:
            str: The file path of the saved PDF.

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

        try:
            await self.initialize()
            await self.page.goto(url, wait_until="networkidle")
            
            file_path = self._generate_file_path(save_dir, url)
            await self._generate_and_save_pdf(file_path)
            
            self.logger.info(f"PDF generated and saved to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            raise
        finally:
            await self.cleanup()

    def _generate_file_path(self, directory, url):
        """
        Generate a file path for the PDF.

        Args:
            directory (str): The directory to save the PDF in.
            url (str): The URL of the webpage (used to generate a filename).

        Returns:
            str: The generated file path.
        """
        filename = f"webpage_pdf_{hash(url)}.pdf"
        return os.path.join(directory, filename)

    async def _generate_and_save_pdf(self, file_path):
        """
        Generate a PDF of the current page and save it to a file.

        Args:
            file_path (str): The path to save the PDF to.
        """
        await self.page.pdf(path=file_path, format='A4')