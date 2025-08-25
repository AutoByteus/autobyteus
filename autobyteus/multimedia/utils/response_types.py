from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ImageGenerationResponse:
    """Response for image generation or editing."""
    image_urls: List[str]
    revised_prompt: Optional[str] = None

@dataclass
class SpeechGenerationResponse:
    """Response for speech generation (Text-to-Speech)."""
    audio_urls: List[str]
