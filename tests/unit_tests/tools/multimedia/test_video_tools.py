from pathlib import Path
from types import SimpleNamespace

import pytest

from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.response_types import VideoGenerationResponse
from autobyteus.multimedia.video.base_video_client import BaseVideoClient
from autobyteus.multimedia.video.video_client_factory import (
    DEFAULT_VIDEO_MODEL_NAME,
    VideoClientFactory,
)
from autobyteus.multimedia.video.video_model import VideoModel
from autobyteus.tools.multimedia import video_tools
from autobyteus.tools.multimedia import GenerateImageTool, EditImageTool, GenerateSpeechTool
from autobyteus.tools.multimedia.video_tools import GenerateVideoTool
from autobyteus.tools.registry import default_tool_registry
from autobyteus.utils.parameter_schema import ParameterDefinition, ParameterSchema, ParameterType


class _MockWorkspace:
    def __init__(self, base_path: Path):
        self._base_path = base_path

    def get_base_path(self) -> str:
        return str(self._base_path)


class _RecordingVideoClient(BaseVideoClient):
    def __init__(self):
        self.generate_calls = []
        self.cleanup_called = False

    async def generate_video(
        self,
        prompt,
        input_image_urls=None,
        input_audio_urls=None,
        input_video_urls=None,
        generation_config=None,
        **kwargs
    ):
        self.generate_calls.append(
            {
                "prompt": prompt,
                "input_image_urls": input_image_urls,
                "input_audio_urls": input_audio_urls,
                "input_video_urls": input_video_urls,
                "generation_config": generation_config,
            }
        )
        return VideoGenerationResponse(video_urls=["data:video/mp4;base64,AAAA"])

    async def cleanup(self):
        self.cleanup_called = True


@pytest.fixture(autouse=True)
def reset_video_factory(monkeypatch):
    monkeypatch.delenv("DEFAULT_VIDEO_GENERATION_MODEL", raising=False)
    VideoClientFactory._initialized = True
    VideoClientFactory._models_by_identifier.clear()
    yield
    VideoClientFactory._initialized = False
    VideoClientFactory._models_by_identifier.clear()


def _register_model(name=DEFAULT_VIDEO_MODEL_NAME, parameter_schema=None) -> VideoModel:
    model = VideoModel(
        name=name,
        value=name,
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=_RecordingVideoClient,
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://video-host:8000",
        parameter_schema=parameter_schema,
        description="Test video model.",
    )
    VideoClientFactory.register_model(model)
    return model


def test_generate_video_tool_is_registered():
    definition = default_tool_registry.get_tool_definition("generate_video")

    assert definition is not None
    assert definition.tool_class is GenerateVideoTool


def test_existing_multimedia_tool_exports_remain_available():
    assert GenerateImageTool is not None
    assert EditImageTool is not None
    assert GenerateSpeechTool is not None


def test_generate_video_tool_schema_omits_generation_config_for_empty_model_schema():
    _register_model()

    schema = GenerateVideoTool.get_argument_schema()
    params = {param.name: param for param in schema.parameters}

    assert {"prompt", "output_file_path", "input_images", "input_audios", "input_videos"}.issubset(params)
    assert "generation_config" not in params


def test_generate_video_tool_schema_includes_generation_config_for_parameterized_model(monkeypatch):
    model = _register_model(
        name="parameterized-video",
        parameter_schema=ParameterSchema(parameters=[
            ParameterDefinition(
                name="duration_seconds",
                param_type=ParameterType.INTEGER,
                description="Video duration.",
                default_value=8,
            )
        ]),
    )
    monkeypatch.setenv("DEFAULT_VIDEO_GENERATION_MODEL", model.model_identifier)

    schema = GenerateVideoTool.get_argument_schema()
    params = {param.name: param for param in schema.parameters}

    assert "generation_config" in params
    generation_config = params["generation_config"]
    assert generation_config.param_type == ParameterType.OBJECT
    assert generation_config.object_schema.get_parameter("duration_seconds").default_value == 8


@pytest.mark.asyncio
async def test_generate_video_tool_execute_splits_inputs_and_saves_output(monkeypatch, tmp_path):
    model = _register_model(name="tool-video")
    monkeypatch.setenv("DEFAULT_VIDEO_GENERATION_MODEL", model.model_identifier)
    recording_client = _RecordingVideoClient()
    monkeypatch.setattr(
        video_tools.video_client_factory,
        "create_video_client",
        lambda model_identifier: recording_client,
    )

    tool = GenerateVideoTool()
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))

    result = await tool.execute(
        context,
        prompt="Animate this tiny scene.",
        input_images=" image.png,https://example.com/ref.png ",
        input_audios=" voice.wav ",
        input_videos=" clip.mp4 ",
        output_file_path="videos/out.mp4",
    )

    saved_path = Path(result["file_path"])
    assert saved_path.exists()
    assert saved_path.name == "out.mp4"
    assert recording_client.generate_calls == [
        {
            "prompt": "Animate this tiny scene.",
            "input_image_urls": ["image.png", "https://example.com/ref.png"],
            "input_audio_urls": ["voice.wav"],
            "input_video_urls": ["clip.mp4"],
            "generation_config": None,
        }
    ]


@pytest.mark.asyncio
async def test_generate_video_tool_raises_when_no_video_urls(monkeypatch, tmp_path):
    model = _register_model(name="empty-video")
    monkeypatch.setenv("DEFAULT_VIDEO_GENERATION_MODEL", model.model_identifier)

    class EmptyVideoClient(_RecordingVideoClient):
        async def generate_video(self, **kwargs):
            return VideoGenerationResponse(video_urls=[])

    monkeypatch.setattr(
        video_tools.video_client_factory,
        "create_video_client",
        lambda model_identifier: EmptyVideoClient(),
    )

    tool = GenerateVideoTool()
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))

    with pytest.raises(ValueError, match="failed to return any video URLs"):
        await tool.execute(
            context,
            prompt="Animate this tiny scene.",
            output_file_path="videos/out.mp4",
        )
