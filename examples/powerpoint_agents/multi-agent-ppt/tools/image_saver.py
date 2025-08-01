import os
import logging
from typing import List
from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

logger = logging.getLogger(__name__)

@tool(name="ImageSaver", category=ToolCategory.FILE_SYSTEM)
async def save_images(image_bytes_list: List[bytes], directory: str, base_filename: str) -> List[str]:
    """
    Saves a list of image bytes to a directory.

    Args:
        image_bytes_list: A list of image bytes.
        directory: The directory to save the images to.
        base_filename: The base filename to use for the images.

    Returns:
        A list of file paths for the saved images.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_paths = []
    for i, image_bytes in enumerate(image_bytes_list):
        file_path = os.path.join(directory, f"{base_filename}_{i}.png")
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        file_paths.append(file_path)

    return file_paths