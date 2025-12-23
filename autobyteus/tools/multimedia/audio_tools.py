import os
import logging
from typing import Optional, List, Any
from pathlib import Path

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia.audio import audio_client_factory, AudioModel, AudioClientFactory
from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
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
    Retrieves a model identifier from an environment variable.
    """
    model_identifier = os.getenv(env_var)
    if not model_identifier:
        if default_model:
            return default_model
        raise ValueError(f"The '{env_var}' environment variable is not set. Please configure it.")
    return model_identifier


def _build_dynamic_audio_schema(base_params: List[ParameterDefinition], model_env_var: str, default_model: str) -> ParameterSchema:
    """
    Builds a tool schema dynamically based on a configured audio model.
    """
    try:
        model_identifier = _get_configured_model_identifier(model_env_var, default_model)
        AudioClientFactory.ensure_initialized()
        model = AudioModel[model_identifier]
    except (ValueError, KeyError) as e:
        logger.error(f"Cannot generate audio tool schema. Check environment and model registry. Error: {e}")
        raise RuntimeError(f"Failed to configure audio tool. Error: {e}")

    # The model's parameter schema is now a ParameterSchema object, so we can use it directly.
    config_schema = model.parameter_schema

    schema = ParameterSchema()
    for param in base_params:
        schema.add_parameter(param)
    
    if config_schema.parameters:
        schema.add_parameter(ParameterDefinition(
            name="generation_config",
            param_type=ParameterType.OBJECT,
            description=f"Model-specific parameters for the configured '{model_identifier}' model.",
            required=False,
            object_schema=config_schema
        ))
    return schema


class GenerateSpeechTool(BaseTool):
    """
    An agent tool for generating speech from text using a Text-to-Speech (TTS) model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_SPEECH_GENERATION_MODEL"
    DEFAULT_MODEL = "gemini-2.5-flash-tts"

    def __init__(self, config=None):
        super().__init__(config)
        self._client: Optional[BaseAudioClient] = None

    @classmethod
    def get_name(cls) -> str:
        return "generate_speech"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Generates spoken audio from text using the system's default Text-to-Speech (TTS) model. "
            "Saves the generated audio file (.wav or .mp3) to the specified local file path and returns the path."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description=(
                    "The text to be converted into spoken audio. For multi-speaker mode, you must format the prompt "
                    "with speaker labels that match the speakers defined in 'speaker_mapping'. "
                    "CRITICAL: Each speaker's dialogue MUST be on a new line. "
                    "Example: 'Joe: Hello Jane.\nJane: Hi Joe, how are you?'"
                ),
                required=True
            ),
            ParameterDefinition(
                name="output_file_path",
                param_type=ParameterType.STRING,
                description=(
                    "Required. The local file path (relative to workspace) where the generated audio should be saved. "
                    "Example: 'assets/audio/speech.wav'"
                ),
                required=True
            )
        ]
        return _build_dynamic_audio_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(
        self,
        context,
        prompt: str,
        output_file_path: str,
        generation_config: Optional[dict] = None,
    ) -> Any:
        model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)
        logger.info(f"generate_speech executing with configured model '{model_identifier}'.")
        if self._client is None:
            self._client = audio_client_factory.create_audio_client(model_identifier=model_identifier)

        response = await self._client.generate_speech(prompt=prompt, generation_config=generation_config)

        if not response.audio_urls:
            raise ValueError("Speech generation failed to return any audio file paths.")

        first_url = response.audio_urls[0]

        if not output_file_path:
            raise ValueError("output_file_path is required but was not provided.")

        # Save to File
        resolved_path = resolve_safe_path(output_file_path, _get_workspace_root(context))
        await download_file_from_url(first_url, resolved_path)

        return {"file_path": str(resolved_path)}

    async def cleanup(self) -> None:
        if self._client:
            await self._client.cleanup()
            self._client = None
