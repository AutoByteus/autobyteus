import os
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from autobyteus.clients.autobyteus_client import AutobyteusClient


class DummyClient:
    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        self.kwargs = kwargs

    async def aclose(self) -> None:
        return None

    def close(self) -> None:
        return None


class DummyResponse:
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self._payload = payload or {"ok": True}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


class RecordingAsyncClient(DummyClient):
    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self.post_calls: list[tuple[str, Dict[str, Any]]] = []

    async def post(self, url: str, json: Dict[str, Any]) -> DummyResponse:
        self.post_calls.append((url, json))
        return DummyResponse()


@pytest.fixture(autouse=True)
def restore_env():
    original = os.environ.copy()
    os.environ["AUTOBYTEUS_API_KEY"] = "test-key"
    yield
    os.environ.clear()
    os.environ.update(original)


def test_missing_api_key_raises_value_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AUTOBYTEUS_API_KEY", raising=False)
    with pytest.raises(ValueError):
        AutobyteusClient(server_url="https://example.com")


def test_server_url_override(monkeypatch: pytest.MonkeyPatch):
    os.environ["AUTOBYTEUS_LLM_SERVER_HOSTS"] = "https://env-host-1,https://env-host-2"

    captured: Dict[str, Any] = {}

    def fake_async_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["async"] = kwargs
        return DummyClient(**kwargs)

    def fake_sync_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["sync"] = kwargs
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("httpx.Client", fake_sync_client)

    client = AutobyteusClient(server_url="https://override-host")
    assert client.server_url == "https://override-host"

    assert captured["async"]["verify"] is False
    assert captured["sync"]["verify"] is False


def test_default_server_url_uses_first_host(monkeypatch: pytest.MonkeyPatch):
    os.environ["AUTOBYTEUS_LLM_SERVER_HOSTS"] = "https://first-host,https://second-host"

    monkeypatch.setattr("httpx.AsyncClient", lambda **_: DummyClient())
    monkeypatch.setattr("httpx.Client", lambda **_: DummyClient())

    client = AutobyteusClient()
    assert client.server_url == "https://first-host"


def test_custom_cert_path_enables_verification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("dummy")

    os.environ["AUTOBYTEUS_SSL_CERT_FILE"] = str(cert_path)

    captured: Dict[str, Any] = {}

    def fake_async_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["async"] = kwargs
        return DummyClient(**kwargs)

    def fake_sync_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["sync"] = kwargs
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("httpx.Client", fake_sync_client)

    AutobyteusClient()
    assert captured["async"]["verify"] == str(cert_path)
    assert captured["sync"]["verify"] == str(cert_path)


@pytest.mark.asyncio
async def test_async_context_manager(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: DummyClient())
    monkeypatch.setattr("httpx.Client", lambda **_: DummyClient())

    async with AutobyteusClient() as client:
        assert isinstance(client, AutobyteusClient)


@pytest.mark.asyncio
async def test_send_message_normalizes_media_sources(monkeypatch: pytest.MonkeyPatch):
    recording_client = RecordingAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: recording_client)
    monkeypatch.setattr("httpx.Client", lambda **_: DummyClient())

    async def fake_media_source_to_data_uri(source: str) -> str:
        return f"data:mock;base64,{source}"

    monkeypatch.setattr(
        "autobyteus.clients.autobyteus_client.media_source_to_data_uri",
        fake_media_source_to_data_uri,
    )

    client = AutobyteusClient(server_url="https://example.com")
    await client.send_message(
        conversation_id="conv-1",
        model_name="model-1",
        user_message="hello",
        image_urls=[" image1.png ", "https://example.com/image2.jpg", ""],
        audio_urls=["audio.mp3"],
        video_urls=[123, "video.mp4"],  # type: ignore[list-item]
    )

    assert len(recording_client.post_calls) == 1
    _, payload = recording_client.post_calls[0]
    assert payload["image_urls"] == [
        "data:mock;base64,image1.png",
        "data:mock;base64,https://example.com/image2.jpg",
    ]
    assert payload["audio_urls"] == ["data:mock;base64,audio.mp3"]
    assert payload["video_urls"] == ["data:mock;base64,video.mp4"]


@pytest.mark.asyncio
async def test_generate_image_normalizes_media_sources(monkeypatch: pytest.MonkeyPatch):
    recording_client = RecordingAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: recording_client)
    monkeypatch.setattr("httpx.Client", lambda **_: DummyClient())

    async def fake_media_source_to_data_uri(source: str) -> str:
        return f"data:mock;base64,{source}"

    monkeypatch.setattr(
        "autobyteus.clients.autobyteus_client.media_source_to_data_uri",
        fake_media_source_to_data_uri,
    )

    client = AutobyteusClient(server_url="https://example.com")
    await client.generate_image(
        model_name="image-model",
        prompt="enhance",
        input_image_urls=[" img1.png ", "img2.png"],
        mask_url=" mask.png ",
        generation_config={"size": "1024x1024"},
    )

    assert len(recording_client.post_calls) == 1
    _, payload = recording_client.post_calls[0]
    assert payload["input_image_urls"] == [
        "data:mock;base64,img1.png",
        "data:mock;base64,img2.png",
    ]
    assert payload["mask_url"] == "data:mock;base64,mask.png"
