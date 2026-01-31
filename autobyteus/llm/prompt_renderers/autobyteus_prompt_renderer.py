from typing import List, Dict, Any

from autobyteus.llm.prompt_renderers.base_prompt_renderer import BasePromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole


class AutobyteusPromptRenderer(BasePromptRenderer):
    async def render(self, messages: List[Message]) -> List[Dict[str, Any]]:
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                return [
                    {
                        "content": msg.content or "",
                        "image_urls": list(msg.image_urls),
                        "audio_urls": list(msg.audio_urls),
                        "video_urls": list(msg.video_urls),
                    }
                ]
        raise ValueError("AutobyteusPromptRenderer requires at least one user message.")
