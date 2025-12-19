import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

import pytest

# ---- Minimal stubs to satisfy imports in the Gemini client module ----
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
# Pillow and requests may not be installed in the unit test environment.
sys.modules.setdefault("PIL", MagicMock())
sys.modules.setdefault("PIL.Image", MagicMock())
sys.modules.setdefault("requests", MagicMock())
# OpenAI SDK may be absent in unit test environment.
sys.modules.setdefault("openai", MagicMock())


from autobyteus.multimedia.image.api import gemini_image_client as gi
from autobyteus.multimedia.image.image_client_factory import ImageClientFactory


def _get_gemini_model():
    ImageClientFactory.ensure_initialized()
    return ImageClientFactory._models_by_identifier["gemini-2.5-flash-image"]


class DummyResponsePart:
    def __init__(self, mime: str | None, data: bytes | None):
        self.inline_data = SimpleNamespace(mime_type=mime, data=data) if mime else None


class DummyPromptFeedback:
    def __init__(self, block_reason=None):
        self.block_reason = block_reason


class DummyResponse:
    def __init__(self, parts, block_reason=None):
        self.parts = parts
        self.prompt_feedback = DummyPromptFeedback(block_reason=block_reason)


class DummyModelInstance:
    def __init__(self, response: DummyResponse, capture):
        self._response = response
        self._capture = capture

    async def generate_content_async(self, contents):
        # record contents for assertions if needed
        self._capture["contents"] = contents
        return self._response


class DummyClient:
    def __init__(self, response: DummyResponse, capture):
        self._response = response
        self._capture = capture
        self.aio = MagicMock()

    def get_generative_model(self, model_name: str):
        self._capture["model_name"] = model_name
        return DummyModelInstance(self._response, self._capture)


@pytest.mark.asyncio
async def test_generate_image_returns_data_uri(monkeypatch):
    capture = {}
    response = DummyResponse(
        parts=[DummyResponsePart("image/png", b"\x89PNG")],
        block_reason=None,
    )
    dummy_client = DummyClient(response, capture)
    runtime_info = SimpleNamespace(runtime="api_key")

    monkeypatch.setattr(gi, "initialize_gemini_client_with_runtime", lambda: (dummy_client, runtime_info))
    monkeypatch.setattr(gi, "resolve_model_for_runtime", lambda model_value, modality, runtime=None: model_value)

    model = _get_gemini_model()
    client = gi.GeminiImageClient(model, MagicMock())

    result = await client.generate_image(prompt="draw a cat")

    assert result.image_urls[0].startswith("data:image/png;base64,")
    assert capture["model_name"] == "gemini-2.5-flash-image"
    # contents should include the prompt only (no input images supplied)
    assert capture["contents"] == ["draw a cat"]


@pytest.mark.asyncio
async def test_generate_image_adjusts_model_for_vertex_runtime(monkeypatch):
    capture = {}
    response = DummyResponse(parts=[DummyResponsePart("image/jpeg", b"binary")])
    dummy_client = DummyClient(response, capture)
    runtime_info = SimpleNamespace(runtime="vertex")

    def fake_resolve(model_value, modality, runtime=None):
        capture["resolved_runtime"] = runtime
        return "resolved-model-name"

    monkeypatch.setattr(gi, "initialize_gemini_client_with_runtime", lambda: (dummy_client, runtime_info))
    monkeypatch.setattr(gi, "resolve_model_for_runtime", fake_resolve)

    model = _get_gemini_model()
    client = gi.GeminiImageClient(model, MagicMock())

    await client.generate_image(prompt="hi")

    assert capture["model_name"] == "resolved-model-name"
    assert capture["resolved_runtime"] == "vertex"


@pytest.mark.asyncio
async def test_generate_image_safety_block_raises(monkeypatch):
    capture = {}
    response = DummyResponse(parts=[], block_reason=SimpleNamespace(name="SAFETY"))
    dummy_client = DummyClient(response, capture)
    runtime_info = SimpleNamespace(runtime="api_key")

    monkeypatch.setattr(gi, "initialize_gemini_client_with_runtime", lambda: (dummy_client, runtime_info))
    monkeypatch.setattr(gi, "resolve_model_for_runtime", lambda model_value, modality, runtime=None: model_value)

    client = gi.GeminiImageClient(_get_gemini_model(), MagicMock())

    with pytest.raises(ValueError) as exc:
        await client.generate_image(prompt="disallowed")

    assert "safety" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_edit_image_delegates_to_generate(monkeypatch):
    client = gi.GeminiImageClient.__new__(gi.GeminiImageClient)
    client.generate_image = AsyncMock(return_value="ok")
    client.model = _get_gemini_model()

    result = await gi.GeminiImageClient.edit_image(
        client,
        prompt="p",
        input_image_urls=["http://x/y.png"],
        mask_url="http://mask.png",
    )

    client.generate_image.assert_awaited_once()
    # mask is ignored; generate_image receives prompt and input_image_urls
    args, kwargs = client.generate_image.await_args
    assert args == ()
    assert kwargs["prompt"] == "p"
    assert kwargs["input_image_urls"] == ["http://x/y.png"]
    assert result == "ok"
