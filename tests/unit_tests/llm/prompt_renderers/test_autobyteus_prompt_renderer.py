import pytest

from autobyteus.llm.prompt_renderers.autobyteus_prompt_renderer import AutobyteusPromptRenderer
from autobyteus.llm.utils.messages import Message, MessageRole


@pytest.mark.asyncio
async def test_autobyteus_prompt_renderer_uses_latest_user_message():
    renderer = AutobyteusPromptRenderer()
    messages = [
        Message(role=MessageRole.USER, content="first"),
        Message(role=MessageRole.ASSISTANT, content="ignored"),
        Message(role=MessageRole.USER, content="latest", image_urls=["img.png"]),
    ]

    rendered = await renderer.render(messages)
    assert rendered == [
        {
            "content": "latest",
            "image_urls": ["img.png"],
            "audio_urls": [],
            "video_urls": [],
        }
    ]


@pytest.mark.asyncio
async def test_autobyteus_prompt_renderer_requires_user_message():
    renderer = AutobyteusPromptRenderer()
    messages = [Message(role=MessageRole.ASSISTANT, content="hi")]
    with pytest.raises(ValueError):
        await renderer.render(messages)
