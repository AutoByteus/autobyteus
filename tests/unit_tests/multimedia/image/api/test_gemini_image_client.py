from types import SimpleNamespace

import pytest
from PIL import Image

from autobyteus.multimedia.image.api import gemini_image_client as gemini_image_module
from autobyteus.multimedia.image.api.gemini_image_client import GeminiImageClient
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _DummyAsyncModels:
    def __init__(self):
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        inline_data = SimpleNamespace(data=b"fake-image", mime_type="image/png")
        return SimpleNamespace(
            parts=[SimpleNamespace(inline_data=inline_data)],
            prompt_feedback=None,
        )


class _DummyClient:
    def __init__(self):
        self.aio = SimpleNamespace(models=_DummyAsyncModels())


def _build_client(monkeypatch):
    dummy_client = _DummyClient()
    monkeypatch.setattr(
        gemini_image_module,
        "initialize_gemini_client_with_runtime",
        lambda: (dummy_client, SimpleNamespace(runtime="api_key")),
    )
    model = SimpleNamespace(name="gemini-3.1-flash-image-preview", value="gemini-3.1-flash-image-preview")
    client = GeminiImageClient(model=model, config=MultimediaConfig(params={}))
    return client, dummy_client


@pytest.mark.anyio
async def test_gemini_image_passes_image_config_for_generation(monkeypatch):
    client, dummy_client = _build_client(monkeypatch)

    await client.generate_image(
        "Create a simple product photo.",
        generation_config={"image_config": {"aspect_ratio": "16:9", "image_size": "2K"}},
    )

    config = dummy_client.aio.models.calls[0]["config"]
    assert config.image_config.aspect_ratio == "16:9"
    assert config.image_config.image_size == "2K"
    assert config.response_modalities == ["IMAGE"]


@pytest.mark.anyio
async def test_gemini_image_passes_image_config_for_edit(monkeypatch, tmp_path):
    input_image = tmp_path / "input.png"
    Image.new("RGB", (8, 8), color="blue").save(input_image)
    client, dummy_client = _build_client(monkeypatch)

    await client.edit_image(
        "Change the background to white.",
        input_image_urls=[str(input_image)],
        generation_config={"image_config": {"aspect_ratio": "1:1", "image_size": "2K"}},
    )

    call = dummy_client.aio.models.calls[0]
    config = call["config"]
    assert config.image_config.aspect_ratio == "1:1"
    assert config.image_config.image_size == "2K"
    assert len(call["contents"]) == 2
