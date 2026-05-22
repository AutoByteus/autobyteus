from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.multimedia.video.base_video_client import BaseVideoClient
from autobyteus.multimedia.video.video_model import VideoModel
from autobyteus.utils.parameter_schema import ParameterDefinition, ParameterSchema, ParameterType


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
        return None


def test_video_model_deserializes_dict_schema():
    model = VideoModel(
        name="test-video",
        value="test-video-v1",
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=DummyVideoClient,
        parameter_schema={
            "parameters": [
                {
                    "name": "duration_seconds",
                    "type": "integer",
                    "description": "Duration.",
                    "default_value": 8,
                }
            ]
        },
    )

    assert isinstance(model.parameter_schema, ParameterSchema)
    duration = model.parameter_schema.get_parameter("duration_seconds")
    assert duration.param_type == ParameterType.INTEGER
    assert model.default_config.to_dict() == {"duration_seconds": 8}


def test_video_model_accepts_parameter_schema_object():
    schema = ParameterSchema(parameters=[
        ParameterDefinition(
            name="aspect_ratio",
            param_type=ParameterType.ENUM,
            description="Aspect ratio.",
            enum_values=["16:9", "9:16"],
        )
    ])

    model = VideoModel(
        name="test-video",
        value="test-video-v1",
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=DummyVideoClient,
        parameter_schema=schema,
    )

    assert model.parameter_schema is schema


def test_video_model_identifier_is_host_qualified_for_autobyteus_runtime():
    model = VideoModel(
        name="gemini-omni-app-rpa",
        value="gemini-omni-app",
        provider=MultimediaProvider.AUTOBYTEUS,
        client_class=DummyVideoClient,
        runtime=MultimediaRuntime.AUTOBYTEUS,
        host_url="http://localhost:8000",
    )

    assert model.model_identifier == "gemini-omni-app-rpa@localhost:8000"
    assert isinstance(model.default_config, MultimediaConfig)
