from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ImageGenerationResponse:
    image_urls: List[str]
    revised_prompt: Optional[str] = None
