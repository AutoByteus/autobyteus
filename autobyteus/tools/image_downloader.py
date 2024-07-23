import os
import aiohttp
from datetime import datetime
from autobyteus.tools.base_tool import BaseTool
from PIL import Image
from io import BytesIO
import platform

from autobyteus.utils.file_utils import get_default_download_folder

class ImageDownloader(BaseTool):
    def __init__(self, custom_download_folder=None):
        super().__init__()
        self.default_download_folder = get_default_download_folder()
        self.download_folder = custom_download_folder or self.default_download_folder
        self.supported_formats = ['.jpeg', '.jpg', '.gif', '.png', '.webp']

    def tool_usage(self):
        return f'''ImageDownloader: Downloads an image from a given URL.

Usage: <<<ImageDownloader(url="image_url")>>>

Parameters:
- "image_url": A string containing a direct URL to an image file (must end with {', '.join(self.supported_formats)})

Supported image formats: {', '.join(format.upper()[1:] for format in self.supported_formats)}

Positive examples:
- https://example.com/image.jpg
- https://example.com/photo.png
- https://example.com/animation.gif
- https://example.com/picture.webp

Negative examples (These will not work):
- https://example.com/page_containing_image.html
- https://example.com/image_without_extension
- https://example.com/document.pdf

Note: The URL must be a direct link to the image file, not a webpage containing the image.'''

    def tool_usage_xml(self):
        return f'''ImageDownloader: Downloads an image from a given URL.

Usage:
<command name="ImageDownloader">
    <arg name="url">image_url</arg>
</command>

Parameters:
- "image_url": A string containing a direct URL to an image file (must end with {', '.join(self.supported_formats)})

Supported image formats: {', '.join(format.upper()[1:] for format in self.supported_formats)}

Positive examples:
<command name="ImageDownloader">
    <arg name="url">https://example.com/photo.jpg</arg>
</command>

<command name="ImageDownloader">
    <arg name="url">https://example.com/image.png</arg>
</command>

Negative examples (These will not work):
<command name="ImageDownloader">
    <arg name="url">https://example.com/page_containing_image.html</arg>
</command>

<command name="ImageDownloader">
    <arg name="url">https://example.com/image_without_extension</arg>
</command>


Note: The URL must be a direct link to the image file, not a webpage containing the image.'''

    async def execute(self, **kwargs):
        """
        Download the image from the given URL.

        Args:
            **kwargs: Keyword arguments containing the image URL. The URL should be specified as 'url'.
                      Optionally, a custom download folder can be specified as 'folder'.

        Returns:
            str: The path of the downloaded image file.

        Raises:
            ValueError: If the 'url' keyword argument is not specified or if the image format is not supported.
        """
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        custom_folder = kwargs.get('folder')
        download_folder = custom_folder or self.download_folder

        # Check if the URL ends with a supported format
        if not any(url.lower().endswith(format) for format in self.supported_formats):
            raise ValueError(
                f"Unsupported image format. The URL must end with one of the following extensions: "
                f"{', '.join(self.supported_formats)}. \n"
                f"Provided URL: {url}\n"
                f"Please ensure you're providing a direct link to an image file, not a webpage containing the image."
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    image_bytes = await response.read()

                # Open the image for verification
                with Image.open(BytesIO(image_bytes)) as img:
                    img.verify()  # Verify the image integrity
                    format = img.format

                # Generate a unique filename based on the current timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                extension = os.path.splitext(url)[1].lower()
                filename = f"downloaded_image_{timestamp}{extension}"
                filepath = os.path.join(download_folder, filename)

                # Save the image to a file
                os.makedirs(download_folder, exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)

                return f"The image is downloaded and stored at: {filepath}"
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to download image from {url}. Error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing image from {url}. Error: {str(e)}")