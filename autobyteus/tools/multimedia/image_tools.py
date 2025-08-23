import os
import aiohttp
import logging
from typing import Optional, List
import asyncio

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia import multimedia_client_factory, MultimediaModel, MultimediaClientFactory

logger = logging.getLogger(__name__)


def _get_configured_model_identifier() -> str:
    """
    Retrieves the default image model from environment variables.
    Raises:
        ValueError: If the environment variable is not set.
    """
    model_identifier = os.getenv("DEFAULT_IMAGE_GENERATION_MODEL")
    if not model_identifier:
        raise ValueError(
            "The 'DEFAULT_IMAGE_GENERATION_MODEL' environment variable is not set. "
            "Please configure it with the identifier of the desired image generation model (e.g., 'gpt-image-1')."
        )
    return model_identifier


def _build_dynamic_schema(base_params: List[ParameterDefinition]) -> ParameterSchema:
    """
    Builds the tool schema dynamically based on the configured model.
    """
    try:
        model_identifier = _get_configured_model_identifier()
        MultimediaClientFactory.ensure_initialized()
        model = MultimediaModel[model_identifier]
    except (ValueError, KeyError) as e:
        logger.error(f"Cannot generate tool schema. Please check your environment and model registry. Error: {e}")
        raise RuntimeError(f"Failed to configure multimedia tool. Error: {e}")

    # Build nested schema for generation_config from the model's parameter schema
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

    # Build the main tool schema
    schema = ParameterSchema()
    for param in base_params:
        schema.add_parameter(param)
    
    schema.add_parameter(ParameterDefinition(
        name="generation_config",
        param_type=ParameterType.OBJECT,
        description=f"Model-specific generation parameters for the configured '{model_identifier}' model.",
        required=True,
        object_schema=config_schema.to_json_schema_dict()
    ))
    return schema


class GenerateImageTool(BaseTool):
    """
    An agent tool for generating images from a text prompt using a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA

    @classmethod
    def get_name(cls) -> str:
        return "GenerateImage"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Generates one or more images based on a textual description (prompt) using the system's default image model. "
            "Returns a list of URLs to the generated images upon success."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description="A detailed textual description of the image to generate.",
                required=True
            )
        ]
        return _build_dynamic_schema(base_params)

    async def _execute(self, context, prompt: str, generation_config: dict) -> str:
        model_identifier = _get_configured_model_identifier()
        logger.info(f"GenerateImageTool executing with configured model '{model_identifier}'.")
        client = None
        try:
            client = multimedia_client_factory.create_multimedia_client(model_identifier=model_identifier)
            response = await client.generate_image(prompt, generation_config=generation_config)
            
            if not response.image_urls:
                raise ValueError("Image generation failed to return any image URLs.")
            
            return f"Image generation successful. URLs: {response.image_urls}"
        finally:
            if client:
                await client.cleanup()


class EditImageTool(BaseTool):
    """
    An agent tool for editing an existing image using a text prompt and a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA

    @classmethod
    def get_name(cls) -> str:
        return "EditImage"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Edits an existing image based on a textual description (prompt) using the system's default image model. "
            "A mask can be provided to specify the exact area to edit (inpainting). "
            "Returns a list of URLs to the edited images."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description="A detailed textual description of the edits to apply to the image.",
                required=True
            ),
            ParameterDefinition(
                name="input_image_urls",
                param_type=ParameterType.STRING,
                description="A comma-separated string of URLs to the source images that need to be edited. Some models may only use the first URL.",
                required=True
            ),
            ParameterDefinition(
                name="mask_image_url",
                param_type=ParameterType.STRING,
                description="Optional. A URL to a mask image (PNG). The transparent areas of this mask define where the input image should be edited.",
                required=False
            )
        ]
        return _build_dynamic_schema(base_params)

    async def _execute(self, context, prompt: str, input_image_urls: str, generation_config: dict, mask_image_url: Optional[str] = None) -> str:
        model_identifier = _get_configured_model_identifier()
        logger.info(f"EditImageTool executing with configured model '{model_identifier}'.")
        client = None
        try:
            urls_list = [url.strip() for url in input_image_urls.split(',') if url.strip()]
            if not urls_list:
                raise ValueError("The 'input_image_urls' parameter cannot be empty.")

            client = multimedia_client_factory.create_multimedia_client(model_identifier=model_identifier)
            response = await client.edit_image(
                prompt=prompt,
                input_image_urls=urls_list,
                mask_url=mask_image_url,
                generation_config=generation_config
            )

            if not response.image_urls:
                raise ValueError("Image editing failed to return any image URLs.")

            return f"Image editing successful. URLs: {response.image_urls}"
        finally:
            if client:
                await client.cleanup()
