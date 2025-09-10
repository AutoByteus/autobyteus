import os
import logging
from typing import Optional, List

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia.image import image_client_factory, ImageModel, ImageClientFactory

logger = logging.getLogger(__name__)


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


def _build_dynamic_image_schema(base_params: List[ParameterDefinition], model_env_var: str, default_model: str) -> ParameterSchema:
    """
    Builds the tool schema dynamically based on the configured image model.
    """
    try:
        model_identifier = _get_configured_model_identifier(model_env_var, default_model)
        ImageClientFactory.ensure_initialized()
        model = ImageModel[model_identifier]
    except (ValueError, KeyError) as e:
        logger.error(f"Cannot generate image tool schema. Check environment and model registry. Error: {e}")
        raise RuntimeError(f"Failed to configure image tool. Error: {e}")

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
            description=f"Model-specific generation parameters for the configured '{model_identifier}' model.",
            required=False,
            object_schema=config_schema
        ))
    return schema


class GenerateImageTool(BaseTool):
    """
    An agent tool for generating images from a text prompt using a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_IMAGE_GENERATION_MODEL"
    DEFAULT_MODEL = "gpt-image-1"

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
        return _build_dynamic_image_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(self, context, prompt: str, generation_config: Optional[dict] = None) -> List[str]:
        model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)
        logger.info(f"GenerateImageTool executing with configured model '{model_identifier}'.")
        client = None
        try:
            client = image_client_factory.create_image_client(model_identifier=model_identifier)
            response = await client.generate_image(prompt=prompt, generation_config=generation_config)
            
            if not response.image_urls:
                raise ValueError("Image generation failed to return any image URLs.")
            
            return response.image_urls
        finally:
            if client:
                await client.cleanup()


class EditImageTool(BaseTool):
    """
    An agent tool for editing an existing image using a text prompt and a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_IMAGE_GENERATION_MODEL"
    DEFAULT_MODEL = "gpt-image-1"

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
        return _build_dynamic_image_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(self, context, prompt: str, input_image_urls: str, generation_config: Optional[dict] = None, mask_image_url: Optional[str] = None) -> List[str]:
        model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)
        logger.info(f"EditImageTool executing with configured model '{model_identifier}'.")
        client = None
        try:
            urls_list = [url.strip() for url in input_image_urls.split(',') if url.strip()]
            if not urls_list:
                raise ValueError("The 'input_image_urls' parameter cannot be empty.")

            client = image_client_factory.create_image_client(model_identifier=model_identifier)
            response = await client.edit_image(
                prompt=prompt,
                input_image_urls=urls_list,
                mask_url=mask_image_url,
                generation_config=generation_config
            )

            if not response.image_urls:
                raise ValueError("Image editing failed to return any image URLs.")

            return response.image_urls
        finally:
            if client:
                await client.cleanup()
