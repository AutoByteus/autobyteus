import os
import logging
from typing import Optional, List, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia.video import video_client_factory, VideoClientFactory
from autobyteus.multimedia.video.base_video_client import BaseVideoClient
from autobyteus.utils.download_utils import download_file_from_url
from autobyteus.utils.file_utils import resolve_safe_path

logger = logging.getLogger(__name__)


def _get_workspace_root(context) -> str:
    if not context.workspace:
        error_msg = (
            f"Relative path provided, but no workspace is configured for agent '{context.agent_id}'. "
            "A workspace is required to resolve relative paths."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    base_path = context.workspace.get_base_path()
    if not base_path or not isinstance(base_path, str):
        error_msg = (
            f"Agent '{context.agent_id}' has a configured workspace, but it provided an invalid base path "
            f"('{base_path}'). Cannot resolve relative paths."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    return base_path


def _get_configured_model_identifier(env_var: str, default_model: Optional[str] = None) -> str:
    """
    Retrieves a model identifier from an environment variable, with a fallback to a default.
    """
    model_identifier = os.getenv(env_var)
    if not model_identifier:
        if default_model:
            return default_model
        raise ValueError(f"The '{env_var}' environment variable is not set. Please configure it.")
    return model_identifier


def _split_media_inputs(media_inputs: Optional[str]) -> List[str]:
    if not media_inputs:
        return []
    return [item.strip() for item in media_inputs.split(",") if item.strip()]


def _build_dynamic_video_schema(base_params: List[ParameterDefinition], model_env_var: str, default_model: str) -> ParameterSchema:
    """
    Builds the tool schema dynamically based on the configured video model.
    """
    try:
        model_identifier = _get_configured_model_identifier(model_env_var, default_model)
        model = VideoClientFactory.get_model(model_identifier)
    except (ValueError, KeyError) as e:
        logger.error("Cannot generate video tool schema. Check environment and model registry. Error: %s", e)
        raise RuntimeError(f"Failed to configure video tool. Error: {e}")

    config_schema = model.parameter_schema

    schema = ParameterSchema()
    for param in base_params:
        schema.add_parameter(param)

    if config_schema.parameters:
        schema.add_parameter(ParameterDefinition(
            name="generation_config",
            param_type=ParameterType.OBJECT,
            description=f"Model-specific generation parameters for the configured '{model_identifier}' model.",
            required=False,
            object_schema=config_schema
        ))
    return schema


def _get_model_description_suffix(model_env_var: str, default_model: str) -> str:
    """
    Fetches the configured model's specific description suffix, if available.
    """
    try:
        model_identifier = _get_configured_model_identifier(model_env_var, default_model)
        model = VideoClientFactory.get_model(model_identifier)
        if model.description:
            return f"\n\n**MODEL SPECIFIC CAPABILITIES:** {model.description}"
    except Exception:
        pass
    return ""


class GenerateVideoTool(BaseTool):
    """
    An agent tool for generating videos from a text prompt and optional media references.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_VIDEO_GENERATION_MODEL"
    DEFAULT_MODEL = "gemini-omni-app-rpa"

    def __init__(self, config=None):
        super().__init__(config)
        self._client: Optional[BaseVideoClient] = None
        self._model_identifier: Optional[str] = None

    @classmethod
    def get_name(cls) -> str:
        return "generate_video"

    @classmethod
    def get_description(cls) -> str:
        base_desc = (
            "Generates a video from a text prompt using the configured video generation model. "
            "Optional image, audio, and video inputs can be provided as references or continuation context. "
            "Saves the generated video to the specified local file path and returns the path."
        )
        suffix = _get_model_description_suffix(cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)
        return f"{base_desc}{suffix}"

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description="A detailed textual description of the video to generate.",
                required=True
            ),
            ParameterDefinition(
                name="input_images",
                param_type=ParameterType.STRING,
                description="Optional. A comma-separated string of image locations (URLs or file paths).",
                required=False
            ),
            ParameterDefinition(
                name="input_audios",
                param_type=ParameterType.STRING,
                description="Optional. A comma-separated string of audio locations (URLs or file paths).",
                required=False
            ),
            ParameterDefinition(
                name="input_videos",
                param_type=ParameterType.STRING,
                description="Optional. A comma-separated string of video locations (URLs or file paths).",
                required=False
            ),
            ParameterDefinition(
                name="output_file_path",
                param_type=ParameterType.STRING,
                description=(
                    "Required. The local file path (relative to workspace) where the generated video should be saved. "
                    "Example: 'assets/videos/result.mp4'"
                ),
                required=True
            )
        ]
        return _build_dynamic_video_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(
        self,
        context,
        prompt: str,
        output_file_path: str,
        input_images: Optional[str] = None,
        input_audios: Optional[str] = None,
        input_videos: Optional[str] = None,
        generation_config: Optional[dict] = None,
    ) -> Any:
        if not self._model_identifier:
            self._model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)

        logger.info(
            "generate_video executing with configured model '%s' for agent '%s'.",
            self._model_identifier,
            context.agent_id,
        )

        if self._client is None:
            self._client = video_client_factory.create_video_client(model_identifier=self._model_identifier)

        response = await self._client.generate_video(
            prompt=prompt,
            input_image_urls=_split_media_inputs(input_images),
            input_audio_urls=_split_media_inputs(input_audios),
            input_video_urls=_split_media_inputs(input_videos),
            generation_config=generation_config
        )

        if not response.video_urls:
            raise ValueError("Video generation failed to return any video URLs.")

        if not output_file_path:
            raise ValueError("output_file_path is required but was not provided.")

        resolved_path = resolve_safe_path(output_file_path, _get_workspace_root(context))
        await download_file_from_url(response.video_urls[0], resolved_path)

        return {"file_path": str(resolved_path)}

    async def cleanup(self) -> None:
        if self._client:
            await self._client.cleanup()
            self._client = None
