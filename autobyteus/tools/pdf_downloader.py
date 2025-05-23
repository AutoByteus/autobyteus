 # This was top-level, keep it there.
import os
import logging
import asyncio 
import requests 
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.utils.file_utils import get_default_download_folder

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="PDFDownloader")
async def pdf_downloader( # function name can be pdf_downloader
    context: 'AgentContext', 
    url: str, 
    folder: Optional[str] = None
) -> str:
    """
    Downloads a PDF file from a given URL and saves it locally.
    'url' is the URL of the PDF.
    'folder' (optional) is a custom directory to save the PDF. If not given,
    uses the system's default download folder. Validates Content-Type.
    """
    logger.debug(f"Functional PDFDownloader tool for agent {context.agent_id}, URL: {url}, Folder: {folder}")
    
    current_download_folder = folder if folder else get_default_download_folder()

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, stream=True, timeout=30))
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type:
            response.close()
            raise ValueError(f"The URL does not point to a PDF file. Content-Type: {content_type}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_from_header = None
        if 'Content-Disposition' in response.headers:
            import re
            match = re.search(r'filename=[\'"]?([^\'"\s]+)[\'"]?', response.headers['Content-Disposition'])
            if match: filename_from_header = match.group(1)
        
        if filename_from_header and filename_from_header.lower().endswith(".pdf"):
            import string
            valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
            filename_from_header = ''.join(c for c in filename_from_header if c in valid_chars)[:200]
            filename = f"{timestamp}_{filename_from_header}"
        else:
            filename = f"downloaded_pdf_{timestamp}.pdf"

        save_path = os.path.join(current_download_folder, filename)
        os.makedirs(current_download_folder, exist_ok=True)
        
        def download_and_save_sync():
            with open(save_path, 'wb') as file_handle:
                for chunk in response.iter_content(chunk_size=8192):
                    file_handle.write(chunk)
            response.close()
        
        await loop.run_in_executor(None, download_and_save_sync)

        logger.info(f"PDF successfully downloaded and saved to {save_path}")
        return f"PDF successfully downloaded and saved to {save_path}"
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading PDF from {url}", exc_info=True)
        return f"Error downloading PDF: Timeout occurred for URL {url}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading PDF from {url}: {str(e)}", exc_info=True)
        return f"Error downloading PDF: {str(e)}"
    except ValueError as e:
        logger.error(f"Content type error for PDF from {url}: {str(e)}", exc_info=True)
        return str(e)
    except IOError as e:
        logger.error(f"Error saving PDF to {current_download_folder}: {str(e)}", exc_info=True)
        return f"Error saving PDF: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error downloading PDF from {url}: {str(e)}", exc_info=True)
        return f"An unexpected error occurred: {str(e)}"
    finally:
        if 'response' in locals() and hasattr(response, 'close') and response.raw and not response.raw.closed:
             response.close()
