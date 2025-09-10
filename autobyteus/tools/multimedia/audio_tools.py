import os
import logging
from typing import Optional, List

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia.audio import audio_client_factory, AudioModel, AudioClientFactory

logger = logging.getLogger(__name__)


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

    config_schema = ParameterSchema()
    if model.parameter_schema:
        for name, meta in model.parameter_schema.items():
            param_type_str = meta.get("type", "string").upper()
            param_type = getattr(ParameterType, param_type_str, ParameterType.STRING)
            
            allowed_values = meta.get("allowed_values")
            if param_type == ParameterType.STRING and allowed_values:
                param_type = ParameterType.ENUM

            config_schema.add_parameter(ParameterDefinition(
                name=name,
                param_type=param_type,
                description=meta.get("description", ""),
                required=False,
                default_value=meta.get("default"),
                enum_values=allowed_values
            ))

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

    @classmethod
    def get_name(cls) -> str:
        return "GenerateSpeech"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Generates spoken audio from text using the system's default Text-to-Speech (TTS) model. "
            "Returns a list of local file paths to the generated audio files (.wav) upon success."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description="The text to be converted into spoken audio.",
                required=True
            )
        ]
        return _build_dynamic_audio_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(self, context, prompt: str, generation_config: Optional[dict] = None) -> List[str]:
        model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)
        logger.info(f"GenerateSpeechTool executing with configured model '{model_identifier}'.")
        client = None
        try:
            client = audio_client_factory.create_audio_client(model_identifier=model_identifier)
            response = await client.generate_speech(prompt=prompt, generation_config=generation_config)
            
            if not response.audio_urls:
                raise ValueError("Speech generation failed to return any audio file paths.")
            
            return response.audio_urls
        finally:
            if client:
                await client.cleanup()
