import os
import logging
from typing import List
import google.generativeai as genai
from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

logger = logging.getLogger(__name__)

@tool(name="ImageGenerator", category=ToolCategory.WEB)
async def generate_images(prompt: str, aspect_ratio: str = "16:9", number_of_images: int = 1) -> List[bytes]:
    """
    Generates images using the Gemini 2.0 Flash model.

    Args:
        prompt: The prompt to use for image generation.
        aspect_ratio: The aspect ratio of the generated images.
        number_of_images: The number of images to generate.

    Returns:
        A list of image bytes.
    """
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model_name="gemini-2.0-flash")

        response = await model_instance.generate_content_async(
            f"Create a detailed visual description of: {prompt}. Make it vivid and suitable for image generation."
        )
        enhanced_description = response.text

        from PIL import Image, ImageDraw, ImageFont
        import io

        width, height = (
            (1920, 1080)
            if aspect_ratio == "16:9"
            else (1080, 1920) if aspect_ratio == "9:16" else (1080, 1080)
        )
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        d = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("Arial", 24)
            title_font = ImageFont.truetype("Arial", 36)
        except IOError:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()

        import textwrap

        max_width = width - 100
        char_width = 20
        chars_per_line = max_width // char_width
        wrapped_text = textwrap.fill(enhanced_description, width=chars_per_line)

        d.text(
            (width // 2, 50),
            f"IMAGE: {prompt}",
            fill=(0, 0, 0),
            font=title_font,
            anchor="mt",
        )
        d.text((50, 120), wrapped_text, fill=(0, 0, 0), font=font)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        return [image_bytes]
    except Exception as e:
        logger.error(f"Error generating images with Gemini: {str(e)}")
        raise ValueError(f"Error generating images with Gemini: {str(e)}")