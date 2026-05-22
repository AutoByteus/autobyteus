import pytest

from autobyteus.clients.autobyteus_client import AutobyteusClient
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.response_types import VideoGenerationResponse
from autobyteus.multimedia.video.base_video_client import BaseVideoClient
from autobyteus.multimedia.video.video_client_factory import (
    DEFAULT_VIDEO_MODEL_NAME,
    VideoClientFactory,
)
from autobyteus.multimedia.video.video_model import VideoModel


class DummyVideoClient(BaseVideoClient):
    async def generate_video(
        self,
        prompt,
        input_image_urls=None,
        input_audio_urls=None,
        input_video_urls=None,
        generation_config=None,
        **kwargs
    ):
        return VideoGenerationResponse(video_urls=["data:video/mp4;base64,AAAA"])


@pytest.fixture(autouse=True)
def reset_factory(monkeypatch):
    monkeypatch.delenv("AUTOBYTEUS_LLM_SERVER_HOSTS", raising=False)
    VideoClientFactory._initialized = False
    VideoClientFactory._models_by_identifier.clear()
    yield
    VideoClientFactory._initialized = False
    VideoClientFactory._models_by_identifier.clear()


def _remote_model(name: str, host_url: str) -> VideoModel:
    return VideoModel(
        name=name,
        value=name,
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=DummyVideoClient,
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url=host_url,
    )


def test_default_video_model_is_registered_without_remote_discovery():
    VideoClientFactory.ensure_initialized()

    model = VideoClientFactory.get_model(DEFAULT_VIDEO_MODEL_NAME)

    assert model.name == DEFAULT_VIDEO_MODEL_NAME
    assert model.host_url == AutobyteusClient.DEFAULT_SERVER_URL


def test_unqualified_model_name_resolves_when_single_match():
    VideoClientFactory._initialized = True
    model = _remote_model(DEFAULT_VIDEO_MODEL_NAME, "http://host-one:8000")
    VideoClientFactory.register_model(model)

    resolved = VideoClientFactory.get_model(DEFAULT_VIDEO_MODEL_NAME)

    assert resolved is model


def test_unqualified_model_name_raises_when_ambiguous():
    VideoClientFactory._initialized = True
    VideoClientFactory.register_model(_remote_model(DEFAULT_VIDEO_MODEL_NAME, "http://host-one:8000"))
    VideoClientFactory.register_model(_remote_model(DEFAULT_VIDEO_MODEL_NAME, "http://host-two:8000"))

    with pytest.raises(ValueError, match="Ambiguous video model"):
        VideoClientFactory.get_model(DEFAULT_VIDEO_MODEL_NAME)


def test_create_video_client_uses_resolved_model():
    VideoClientFactory._initialized = True
    model = _remote_model("custom-video", "http://host-one:8000")
    VideoClientFactory.register_model(model)

    client = VideoClientFactory.create_video_client("custom-video")

    assert isinstance(client, DummyVideoClient)
    assert client.model is model
