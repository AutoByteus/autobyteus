import os
import base64
import aiohttp
import asyncio
from datetime import datetime
from autobyteus.tools.base_tool import BaseTool
from PIL import Image
from io import BytesIO
import re

# Ensure PIL has WebP support
from PIL import features
if not features.check('webp'):
    raise ImportError("WebP support is not available in this Pillow installation. "
                      "Please reinstall Pillow with WebP support.")

class ImageDownloader(BaseTool):
    def __init__(self):
        super().__init__()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    def tool_usage(self):
        return 'ImageDownloader: Downloads an image from a given URL or base64-encoded string. Usage: <<<ImageDownloader(url="image_url")>>>, where "image_url" is a string containing either the direct URL of the image or a base64-encoded image string. Supported image formats: JPEG, JPG, GIF, PNG, WebP.'

    def tool_usage_xml(self):
        return '''ImageDownloader: Downloads an image from a given URL or base64-encoded string. Usage:
<command name="ImageDownloader">
  <arg name="url">image_url</arg>
</command>
where "image_url" is a string containing either the direct URL of the image or a base64-encoded image string. Supported image formats: JPEG, JPG, GIF, PNG, WebP.
'''

    def is_base64_image(self, url):
        """
        Check if the URL is a base64-encoded image.
        """
        base64_pattern = r'^data:image/(\w+);base64,'
        return bool(re.match(base64_pattern, url))

    async def execute(self, **kwargs):
        """
        Download the image from the given URL or base64-encoded string.

        Args:
            **kwargs: Keyword arguments containing the image URL. The URL should be specified as 'url'.

        Returns:
            str: The path of the downloaded image file.

        Raises:
            ValueError: If the 'url' keyword argument is not specified or if the image format is not supported.
        """
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        supported_formats = ['.jpeg', '.jpg', '.gif', '.png', '.webp']

        try:
            if self.is_base64_image(url):
                # Handle base64-encoded image
                image_format = re.match(r'^data:image/(\w+);base64,', url).group(1)
                if f'.{image_format}' not in supported_formats:
                    raise ValueError(f"Unsupported image format. Supported formats: {', '.join(supported_formats)}")
                
                # Extract base64 data
                base64_data = re.sub(r'^data:image/\w+;base64,', '', url)
                image_bytes = base64.b64decode(base64_data)
            else:
                # Handle regular URL
                if not self.session:
                    self.session = aiohttp.ClientSession()
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    image_bytes = await response.read()

            # Open the image for verification
            with Image.open(BytesIO(image_bytes)) as img:
                img.verify()  # Verify the image integrity
                format = img.format
                mode = img.mode

            # Reopen the image for processing and saving
            image = Image.open(BytesIO(image_bytes))
            
            # For WebP images, convert to RGB mode if it's not already
            if format.lower() == 'webp' and mode not in ('RGB', 'RGBA'):
                image = image.convert('RGB')

            # Generate a unique filename based on the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = f".{format.lower()}"
            filename = f"downloaded_image_{timestamp}{extension}"
            filepath = os.path.join("downloads", filename)

            # Save the image to a file
            os.makedirs("downloads", exist_ok=True)
            image.save(filepath, format=format)

            return filepath
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to download image from {url}. Error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing image from {url}. Error: {str(e)}")

    async def close(self):
        if self.session:
            await self.session.close()