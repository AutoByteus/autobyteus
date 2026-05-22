import pytest

from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.multimedia.video.api.autobyteus_video_client import AutobyteusVideoClient
from autobyteus.multimedia.video.video_model import VideoModel


class _DummyAutobyteusClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.generate_calls = []
        self.cleanup_calls = []
        self.closed = False
        _DummyAutobyteusClient.last_instance = self

    async def generate_video(self, **kwargs):
        self.generate_calls.append(kwargs)
        return {"video_urls": ["data:video/mp4;base64,AAAA"]}

    async def cleanup_video_session(self, session_id):
        self.cleanup_calls.append(session_id)
        return {"success": True}

    async def close(self):
        self.closed = True


def _model():
    return VideoModel(
        name="gemini-omni-app-rpa",
        value="gemini-omni-app",
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=AutobyteusVideoClient,
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://video-host:8000",
    )


@pytest.mark.asyncio
async def test_autobyteus_video_client_delegates_generate_video(monkeypatch):
    monkeypatch.setattr(
        "autobyteus.multimedia.video.api.autobyteus_video_client.AutobyteusClient",
        _DummyAutobyteusClient,
    )
    client = AutobyteusVideoClient(model=_model(), config=MultimediaConfig())

    response = await client.generate_video(
        prompt="Animate the scene.",
        input_image_urls=["image.png"],
        input_audio_urls=["audio.wav"],
        input_video_urls=["clip.mp4"],
        generation_config={"duration_seconds": 8},
    )

    assert response.video_urls == ["data:video/mp4;base64,AAAA"]
    dummy = _DummyAutobyteusClient.last_instance
    assert dummy.server_url == "http://video-host:8000"
    assert dummy.generate_calls == [
        {
            "model_name": "gemini-omni-app-rpa",
            "prompt": "Animate the scene.",
            "input_image_urls": ["image.png"],
            "input_audio_urls": ["audio.wav"],
            "input_video_urls": ["clip.mp4"],
            "generation_config": {"duration_seconds": 8},
            "session_id": client.session_id,
        }
    ]


@pytest.mark.asyncio
async def test_autobyteus_video_client_raises_when_no_video_urls(monkeypatch):
    class EmptyVideoClient(_DummyAutobyteusClient):
        async def generate_video(self, **kwargs):
            return {"video_urls": []}

    monkeypatch.setattr(
        "autobyteus.multimedia.video.api.autobyteus_video_client.AutobyteusClient",
        EmptyVideoClient,
    )
    client = AutobyteusVideoClient(model=_model(), config=MultimediaConfig())

    with pytest.raises(ValueError, match="did not return any video URLs"):
        await client.generate_video(prompt="Animate.")


@pytest.mark.asyncio
async def test_autobyteus_video_client_cleanup_notifies_server(monkeypatch):
    monkeypatch.setattr(
        "autobyteus.multimedia.video.api.autobyteus_video_client.AutobyteusClient",
        _DummyAutobyteusClient,
    )
    client = AutobyteusVideoClient(model=_model(), config=MultimediaConfig())

    await client.cleanup()

    dummy = _DummyAutobyteusClient.last_instance
    assert dummy.cleanup_calls == [client.session_id]
    assert dummy.closed is True
