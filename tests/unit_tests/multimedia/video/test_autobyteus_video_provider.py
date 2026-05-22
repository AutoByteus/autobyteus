from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.video.autobyteus_video_provider import AutobyteusVideoModelProvider
from autobyteus.multimedia.video.video_client_factory import VideoClientFactory


class _DummySyncClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _DummyAutobyteusClient:
    instances = []

    def __init__(self, server_url):
        self.server_url = server_url
        self.sync_client = _DummySyncClient()
        _DummyAutobyteusClient.instances.append(self)

    def get_available_video_models_sync(self):
        return {
            "models": [
                {
                    "name": "gemini-omni-app-rpa",
                    "value": "gemini-omni-app",
                    "provider": "AUTOBYTEUS",
                    "parameter_schema": {"parameters": []},
                    "description": "Video model.",
                },
                {
                    "name": "malformed-video",
                    "value": "malformed-video",
                    "provider": "AUTOBYTEUS",
                },
            ]
        }


def test_discover_and_register_video_models(monkeypatch):
    VideoClientFactory._initialized = True
    VideoClientFactory._models_by_identifier.clear()
    _DummyAutobyteusClient.instances.clear()

    monkeypatch.setenv("AUTOBYTEUS_LLM_SERVER_HOSTS", "http://video-host:8000")
    monkeypatch.setattr(
        "autobyteus.multimedia.video.autobyteus_video_provider.AutobyteusClient",
        _DummyAutobyteusClient,
    )

    AutobyteusVideoModelProvider.discover_and_register()

    model = VideoClientFactory.get_model("gemini-omni-app-rpa")
    assert model.model_identifier == "gemini-omni-app-rpa@video-host:8000"
    assert model.runtime == MultimediaRuntime.AUTOBYTEUS
    assert model.description == "Video model."
    assert len(model.parameter_schema.parameters) == 0
    assert _DummyAutobyteusClient.instances[0].sync_client.closed is True
    assert "malformed-video" not in VideoClientFactory._models_by_identifier
