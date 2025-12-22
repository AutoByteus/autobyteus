import logging
import aiohttp
import base64
import shutil
import os
from pathlib import Path

logger = logging.getLogger(__name__)

async def download_file_from_url(url: str, file_path: Path) -> None:
    """
    Asynchronously downloads a file from a URL, decodes a data URI, or copies a local file 
    to a specified file path.
    
    Features:
    - Supports http/https URLs, data: URIs (base64), and local file paths.
    - Creates parent directories if they don't exist.
    - Uses streaming for HTTP URLs to handle large files efficiently.
    - Guarantees cleanup of partial files on failure.
    
    Args:
        url: The source URL, data URI, or local path.
        file_path: The specific local path (including filename) to save to.
        
    Raises:
        IOError: If download, decoding, or copying fails.
    """
    # Ensure parent directory exists
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory structure for {file_path}: {e}")
        raise IOError(f"Filesystem error: {e}")

    try:
        if url.startswith("data:"):
            # Handle Data URI
            try:
                header, encoded = url.split(",", 1)
                data = base64.b64decode(encoded)
                with open(file_path, "wb") as f:
                    f.write(data)
                logger.info(f"Successfully decoded and saved data URI to: {file_path}")
                return
            except Exception as e:
                logger.error(f"Failed to decode data URI: {e}")
                raise IOError(f"Invalid data URI format: {e}")

        if os.path.exists(url) and os.path.isfile(url):
            # Handle Local File Path (Copy)
            try:
                shutil.copy(url, file_path)
                logger.info(f"Successfully copied local file from {url} to {file_path}")
                return
            except Exception as e:
                logger.error(f"Failed to copy local file from {url} to {file_path}: {e}")
                raise IOError(f"File copy error: {e}")

        # Handle HTTP URL
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise IOError(f"Failed to download from {url}: HTTP {response.status}")
                
                # Open file for writing binary
                with open(file_path, "wb") as f:
                    # Iterate over chunks to avoid loading large files into memory
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        
        logger.info(f"Successfully downloaded file to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to process media from {url} to {file_path}: {e}")
        # Cleanup: Delete the partial/empty file if it was created
        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up partial file: {file_path}")
            except OSError as cleanup_error:
                logger.warning(f"Failed to clean up partial file {file_path}: {cleanup_error}")
        raise
