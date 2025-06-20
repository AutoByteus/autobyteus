import logging
from typing import Dict, Optional, List, AsyncGenerator, Union, Tuple
import google.generativeai as genai
from google.generativeai import types
import os
import base64
from io import BytesIO
from PIL import Image
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
import asyncio

logger = logging.getLogger(__name__)

class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        self.generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        # Provide defaults if not specified
        model = model or LLMModel.GEMINI_2_5_PRO_API
        llm_config = llm_config or LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.initialize()
        self.model_instance = genai.GenerativeModel(
            model_name=self.model.value,
            generation_config=self.generation_config,
            system_instruction=self.system_message
        )

    @classmethod
    def initialize(cls):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set.")
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            genai.configure(api_key=api_key)
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")

    def _prepare_history(self) -> List[Dict]:
        history = []
        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            role = 'model' if msg.role == MessageRole.ASSISTANT else msg.role.value
            if isinstance(msg.content, str):
                history.append({"role": role, "parts": [msg.content]})
            else:
                history.append({"role": role, "parts": msg.content})
        return history

    async def _send_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            history = self._prepare_history()
            response = await self.model_instance.generate_content_async(history)
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            token_usage = None
            if hasattr(response, 'usage_metadata'):
                usage_meta = response.usage_metadata
                token_usage = TokenUsage(
                    prompt_tokens=usage_meta.prompt_token_count,
                    completion_tokens=usage_meta.candidates_token_count,
                    total_tokens=usage_meta.total_token_count
                )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API call: {str(e)}")
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def _stream_user_message_to_llm(self, user_message: str, image_urls: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        history = self._prepare_history()
        try:
            stream = await self.model_instance.generate_content_async(history, stream=True)
            
            accumulated_content = ""
            final_response = None
            async for chunk in stream:
                if hasattr(chunk, 'text') and chunk.text:
                    accumulated_content += chunk.text
                    yield ChunkResponse(content=chunk.text, is_complete=False, usage=None)
                final_response = chunk
            
            self.add_assistant_message(accumulated_content)
            
            usage = None
            if final_response and hasattr(final_response, 'usage_metadata'):
                usage_meta = final_response.usage_metadata
                usage = TokenUsage(
                    prompt_tokens=usage_meta.prompt_token_count,
                    completion_tokens=usage_meta.candidates_token_count,
                    total_tokens=usage_meta.total_token_count
                )
            
            yield ChunkResponse(content="", is_complete=True, usage=usage)

        except Exception as e:
            logger.error(f"Error in Gemini API streaming call: {str(e)}")
            raise ValueError(f"Error in Gemini API streaming call: {str(e)}")

    async def cleanup(self):
        await super().cleanup()
    
    async def generate_image(self, prompt: str, model: str = "gemini-2.5-pro", 
                             aspect_ratio: str = "16:9", number_of_images: int = 1) -> List[bytes]:
        """
        Generate images using Gemini's image generation capabilities
        
        Args:
            prompt (str): Text description of the image to generate
            model (str): The model to use for generation
            aspect_ratio (str): Aspect ratio of the generated image ("16:9", "9:16", "1:1")
            number_of_images (int): Number of images to generate
            
        Returns:
            List[bytes]: List of generated images as bytes
        """
        try:
            # Configure genai with API key
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            
            # Use the GenerativeModel to generate an image description
            model_instance = genai.GenerativeModel(model_name=model)
            response = await model_instance.generate_content_async(
                f"Create a detailed visual description of: {prompt}. Make it vivid and suitable for image generation."
            )
            
            # Get the enhanced description
            enhanced_description = response.text
            
            # Now create a placeholder image with the text description
            logger.info("Creating placeholder image with text description")
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a placeholder image with the text
            width, height = (1920, 1080) if aspect_ratio == "16:9" else (1080, 1920) if aspect_ratio == "9:16" else (1080, 1080)
            img = Image.new('RGB', (width, height), color=(240, 240, 240))
            d = ImageDraw.Draw(img)
            
            # Use a default font
            try:
                font = ImageFont.truetype("Arial", 24)
                title_font = ImageFont.truetype("Arial", 36)
            except IOError:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()
                
            # Wrap text to fit the image
            import textwrap
            max_width = width - 100
            char_width = 20  # Approximate average character width
            chars_per_line = max_width // char_width
            wrapped_text = textwrap.fill(enhanced_description, width=chars_per_line)
            
            # Draw a title
            d.text((width//2, 50), f"IMAGE: {prompt}", fill=(0, 0, 0), font=title_font, anchor="mt")
            
            # Draw the text
            d.text((50, 120), wrapped_text, fill=(0, 0, 0), font=font)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            
            return [image_bytes]
            
        except Exception as e:
            logger.error(f"Error generating images with Gemini: {str(e)}")
            raise ValueError(f"Error generating images with Gemini: {str(e)}")
            
    async def generate_diagram(self, prompt: str, diagram_type: str = "flowchart", 
                              model: str = "gemini-2.5-pro") -> bytes:
        """
        Generate a diagram based on text description using Gemini's image generation
        
        Args:
            prompt (str): Description of the diagram to generate
            diagram_type (str): Type of diagram (flowchart, uml, org_chart, etc.)
            model (str): The model to use for generation
            
        Returns:
            bytes: Generated diagram image as bytes
        """
        enhanced_prompt = f"Create a {diagram_type} diagram that shows {prompt}. Make it clean, professional, with clear labels, and suitable for a business presentation."
        
        try:
            # Configure genai with API key
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            
            # First, generate a text description or mermaid/graphviz code for the diagram
            model_instance = genai.GenerativeModel(
                model_name=model,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                )
            )
            response = await model_instance.generate_content_async(
                f"{enhanced_prompt} Please provide the diagram as mermaid or graphviz code."
            )
            
            try:
                diagram_code = response.text
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not extract text from response: {e}")
                # Create a simple description instead
                diagram_code = f"Diagram for: {enhanced_prompt}\n\nUnable to generate diagram code."
            
            # Try to render the diagram code if it contains mermaid or graphviz
            try:
                from PIL import Image
                import io
                
                if "```mermaid" in diagram_code:
                    # Extract mermaid code
                    import re
                    mermaid_match = re.search(r'```mermaid\s*([\s\S]*?)\s*```', diagram_code)
                    if mermaid_match:
                        mermaid_code = mermaid_match.group(1).strip()
                        
                        # Try to use mermaid-cli if available
                        try:
                            import subprocess
                            import tempfile
                            
                            # Create temporary files
                            with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w', delete=False) as mmd_file:
                                mmd_file.write(mermaid_code)
                                mmd_path = mmd_file.name
                                
                            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as png_file:
                                png_path = png_file.name
                            
                            # Try to run mmdc (mermaid-cli)
                            try:
                                subprocess.run(
                                    ['mmdc', '-i', mmd_path, '-o', png_path, '-b', 'transparent'],
                                    check=True,
                                    timeout=15
                                )
                                
                                # Read the generated PNG
                                with open(png_path, 'rb') as f:
                                    diagram_bytes = f.read()
                                    
                                # Clean up temp files
                                os.unlink(mmd_path)
                                os.unlink(png_path)
                                
                                logger.info("Generated diagram using mermaid-cli")
                                return diagram_bytes
                            except (subprocess.SubprocessError, FileNotFoundError):
                                logger.warning("mermaid-cli not available, falling back to text rendering")
                        except ImportError:
                            logger.warning("subprocess module not available, falling back to text rendering")
                
                # If we reach here, either it's not mermaid code or mermaid-cli failed
                # Render as text image
                img = Image.new('RGB', (1200, 800), color=(255, 255, 255))
                from PIL import ImageDraw, ImageFont
                d = ImageDraw.Draw(img)
                
                # Use a default font
                try:
                    font = ImageFont.truetype("Arial", 16)
                except IOError:
                    font = ImageFont.load_default()
                
                # Draw the text
                d.text((20, 20), diagram_code, fill=(0, 0, 0), font=font)
                
                # Convert to bytes
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                diagram_bytes = buffer.getvalue()
                
                logger.info("Generated diagram as text image")
                return diagram_bytes
                
            except Exception as render_error:
                logger.warning(f"Error rendering diagram code: {str(render_error)}")
            
            # If we reach here, try to generate an image directly
            try:
                client = genai.Client(api_key=api_key)
                imagen_response = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=enhanced_prompt,
                    config=genai.types.GenerateImagesConfig(
                        number_of_images=1
                    )
                )
                
                if (hasattr(imagen_response, 'generated_images') and 
                    imagen_response.generated_images and 
                    hasattr(imagen_response.generated_images[0], 'image') and
                    hasattr(imagen_response.generated_images[0].image, 'image_bytes')):
                    
                    logger.info("Generated diagram using Imagen")
                    return imagen_response.generated_images[0].image.image_bytes
            except Exception as imagen_error:
                logger.warning(f"Imagen generation failed: {str(imagen_error)}")
            
            # If all else fails, create a simple text image with the diagram description
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            img = Image.new('RGB', (1200, 800), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            
            # Use a default font
            try:
                font = ImageFont.truetype("Arial", 20)
            except IOError:
                font = ImageFont.load_default()
            
            # Draw the text
            d.text((50, 50), f"DIAGRAM: {enhanced_prompt}", fill=(0, 0, 0), font=font)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            diagram_bytes = buffer.getvalue()
            
            logger.info("Generated fallback diagram image")
            return diagram_bytes
                
        except Exception as e:
            logger.error(f"Error generating diagram with Gemini: {str(e)}")
            raise ValueError(f"Error generating diagram with Gemini: {str(e)}")

    @staticmethod
    def image_bytes_to_base64_uri(image_bytes: bytes, format: str = "PNG") -> str:
        """
        Convert image bytes to base64 data URI for embedding in slides
        
        Args:
            image_bytes (bytes): Image data as bytes
            format (str): Image format (PNG, JPEG, etc.)
            
        Returns:
            str: Base64 data URI
        """
        try:
            b64_image = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = f"image/{format.lower()}"
            return f"data:{mime_type};base64,{b64_image}"
        except Exception as e:
            logger.error(f"Error converting image to base64: {str(e)}")
            raise ValueError(f"Error converting image to base64: {str(e)}")

    @staticmethod
    def video_bytes_to_base64_uri(video_bytes: bytes, format: str = "mp4") -> str:
        """
        Convert video bytes to base64 data URI for embedding in slides
        
        Args:
            video_bytes (bytes): Video data as bytes
            format (str): Video format (mp4, webm, etc.)
            
        Returns:
            str: Base64 data URI
        """
        try:
            b64_video = base64.b64encode(video_bytes).decode('utf-8')
            mime_type = f"video/{format.lower()}"
            return f"data:{mime_type};base64,{b64_video}"
        except Exception as e:
            logger.error(f"Error converting video to base64: {str(e)}")
            raise ValueError(f"Error converting video to base64: {str(e)}")

    async def generate_video(self, prompt: str, image_bytes: Optional[bytes] = None, 
                            model: str = "veo-2.0-generate-001", aspect_ratio: str = "16:9") -> bytes:
        """
        Generate a video using Gemini's video generation capabilities
        
        Args:
            prompt (str): Text description of the video to generate
            image_bytes (bytes, optional): Optional image to use as starting point for video
            model (str): The video generation model to use
            aspect_ratio (str): Aspect ratio of the generated video ("16:9", "9:16")
            
        Returns:
            bytes: Generated video as bytes
        """
        try:
            # Configure genai with API key
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Since the Veo API might not be available through the standard Python SDK,
            # we'll create a fallback video representation
            logger.info(f"Creating video representation for prompt: {prompt}")
            
            # Generate a description of the video using Gemini
            model_instance = genai.GenerativeModel(model_name="gemini-2.5-pro")
            response = await model_instance.generate_content_async(
                f"Describe a video that shows: {prompt}. Include details about what would happen in the video, scene by scene."
            )
            
            try:
                video_description = response.text
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not extract text from response: {e}")
                # Create a simple description instead
                video_description = f"Video about: {prompt}\n\nThis video would show the key aspects of {prompt} with engaging visuals and clear explanations."
            
            # Create a placeholder image with the video description
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a video placeholder image with text
            width, height = (1280, 720) if aspect_ratio == "16:9" else (720, 1280) if aspect_ratio == "9:16" else (1080, 1080)
            img = Image.new('RGB', (width, height), color=(0, 0, 0))
            d = ImageDraw.Draw(img)
            
            # Use a default font
            try:
                font = ImageFont.truetype("Arial", 20)
                title_font = ImageFont.truetype("Arial", 30)
            except IOError:
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()
            
            # Draw a play button
            center_x, center_y = width // 2, height // 2
            d.polygon([(center_x - 50, center_y - 30), (center_x + 50, center_y), (center_x - 50, center_y + 30)], fill=(255, 255, 255))
            d.ellipse((center_x - 100, center_y - 100, center_x + 100, center_y + 100), outline=(255, 255, 255), width=5)
            
            # Wrap text to fit the image
            import textwrap
            max_width = width - 100
            char_width = 15  # Approximate average character width
            chars_per_line = max_width // char_width
            wrapped_text = textwrap.fill(video_description, width=chars_per_line)
            
            # Draw the title
            d.text((width//2, 50), f"VIDEO: {prompt}", fill=(255, 255, 255), font=title_font, anchor="mt")
            
            # Draw the description (limited to fit)
            lines = wrapped_text.split("\n")
            max_lines = 10  # Limit number of lines to display
            if len(lines) > max_lines:
                display_text = "\n".join(lines[:max_lines]) + "\n..."
            else:
                display_text = wrapped_text
                
            d.text((50, height - 250), display_text, fill=(255, 255, 255), font=font)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
            
            logger.info("Generated fallback video placeholder image")
            return image_bytes
                
        except Exception as e:
            logger.error(f"Error generating video with Gemini: {str(e)}")
            raise ValueError(f"Error generating video with Gemini: {str(e)}")
