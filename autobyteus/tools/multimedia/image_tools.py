import os
import logging
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.multimedia.image import image_client_factory, ImageModel, ImageClientFactory
from autobyteus.multimedia.image.base_image_client import BaseImageClient
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


class _SharedImageClientManager:
    """
    Internal manager to share image client instances between tools (e.g., Generate and Edit)
    WITHIN the same agent instance.
    
    It keys clients by (agent_id, model_identifier). This ensures that:
    1. Multiple tools (Generate/Edit) used by Agent A share the same client (preserving session/context).
    2. Agent B gets a completely separate client instance, preventing state leakage between agents.
    """
    # Key: (agent_id, model_identifier) -> Client Instance
    _clients: Dict[Tuple[str, str], BaseImageClient] = {}
    # Key: (agent_id, model_identifier) -> Reference Count
    _ref_counts: Dict[Tuple[str, str], int] = {}

    @classmethod
    def get_client(cls, agent_id: str, model_identifier: str) -> BaseImageClient:
        key = (agent_id, model_identifier)
        
        if key not in cls._clients:
            logger.info(f"SharedImageClientManager: Creating new client for model '{model_identifier}' scoped to agent '{agent_id}'.")
            cls._clients[key] = image_client_factory.create_image_client(model_identifier=model_identifier)
            cls._ref_counts[key] = 0
        
        cls._ref_counts[key] += 1
        logger.debug(f"SharedImageClientManager: Client for '{model_identifier}' (Agent: {agent_id}) ref count incremented to {cls._ref_counts[key]}")
        return cls._clients[key]

    @classmethod
    async def release_client(cls, agent_id: str, model_identifier: str) -> None:
        key = (agent_id, model_identifier)
        
        if key in cls._ref_counts:
            cls._ref_counts[key] -= 1
            logger.debug(f"SharedImageClientManager: Client for '{model_identifier}' (Agent: {agent_id}) ref count decremented to {cls._ref_counts[key]}")
            
            if cls._ref_counts[key] <= 0:
                logger.info(f"SharedImageClientManager: Cleaning up client for '{model_identifier}' (Agent: {agent_id})")
                client = cls._clients.pop(key, None)
                del cls._ref_counts[key]
                if client:
                    await client.cleanup()


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

    # The model's parameter schema is now a ParameterSchema object, so we can use it directly.
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
        ImageClientFactory.ensure_initialized()
        model = ImageModel[model_identifier]
        if model.description:
            return f"\n\n**MODEL SPECIFIC CAPABILITIES:** {model.description}"
    except Exception:
        # Fail gracefully if model lookup fails; rely on base tool description
        pass
    return ""


class GenerateImageTool(BaseTool):
    """
    An agent tool for generating images from a text prompt using a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_IMAGE_GENERATION_MODEL"
    DEFAULT_MODEL = "gpt-image-1.5"

    def __init__(self, config=None):
        super().__init__(config)
        self._client: Optional[BaseImageClient] = None
        self._model_identifier: Optional[str] = None

    @classmethod
    def get_name(cls) -> str:
        return "generate_image"

    @classmethod
    def get_description(cls) -> str:
        base_desc = (
            "Generates one or more images based on a textual description (prompt). "
            "This versatile tool handles both creation from scratch and modification of existing images. "
            "If 'input_images' are provided, it serves as a powerful editing and variation engine. "
            "Use cases include: creating or editing posters, modifying scene elements (e.g., 'add a cat to the sofa'), "
            "style transfer (e.g., 'turn this photo into an oil painting'), generating variations of a design, "
            "or any imaging task requiring consistency with an input reference (e.g., preserving a specific composition or background while changing the subject). "
            "Saves the generated image to the specified local file path and returns the path. "
            "Please refer to the specific capabilities of the configured model below to check if it supports "
            "input images for variations/editing."
        )
        suffix = _get_model_description_suffix(cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)
        return f"{base_desc}{suffix}"

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        base_params = [
            ParameterDefinition(
                name="prompt",
                param_type=ParameterType.STRING,
                description="A detailed textual description of the image to generate.",
                required=True
            ),
            ParameterDefinition(
                name="input_images",
                param_type=ParameterType.STRING,
                description="Optional. A comma-separated string of image locations (URLs or file paths).",
                required=False
            ),
            ParameterDefinition(
                name="output_file_path",
                param_type=ParameterType.STRING,
                description=(
                    "Required. The local file path (relative to workspace) where the generated image should be saved. "
                    "Example: 'assets/images/result.png'"
                ),
                required=True
            )
        ]
        return _build_dynamic_image_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(
        self,
        context,
        prompt: str,
        output_file_path: str,
        input_images: Optional[str] = None,
        generation_config: Optional[dict] = None,
    ) -> Any:
        # 1. Resolve Model ID
        if not self._model_identifier:
            self._model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)

        logger.info(f"generate_image executing with configured model '{self._model_identifier}' for agent '{context.agent_id}'.")
        
        # 2. Obtain Shared Client (Scoped to Agent ID)
        if self._client is None:
            self._client = _SharedImageClientManager.get_client(context.agent_id, self._model_identifier)

        # 3. Process Inputs
        urls_list = None
        if input_images:
            urls_list = [url.strip() for url in input_images.split(',') if url.strip()]

        # 4. Execute Generation (client enforces single image where applicable)
        response = await self._client.generate_image(
            prompt=prompt, 
            input_image_urls=urls_list,
            generation_config=generation_config
        )

        if not response.image_urls:
            raise ValueError("Image generation failed to return any image URLs.")

        first_url = response.image_urls[0]

        if not output_file_path:
            raise ValueError("output_file_path is required but was not provided.")

        # 5. Save to File
        resolved_path = resolve_safe_path(output_file_path, _get_workspace_root(context))
        await download_file_from_url(first_url, resolved_path)

        return {"file_path": str(resolved_path)}

    async def cleanup(self) -> None:
        if self._client and self._model_identifier and self.agent_id:
            await _SharedImageClientManager.release_client(self.agent_id, self._model_identifier)
            self._client = None


class EditImageTool(BaseTool):
    """
    An agent tool for editing an existing image using a text prompt and a pre-configured model.
    """
    CATEGORY = ToolCategory.MULTIMEDIA
    MODEL_ENV_VAR = "DEFAULT_IMAGE_EDIT_MODEL"
    DEFAULT_MODEL = "gpt-image-1.5"

    def __init__(self, config=None):
        super().__init__(config)
        self._client: Optional[BaseImageClient] = None
        self._model_identifier: Optional[str] = None

    @classmethod
    def get_name(cls) -> str:
        return "edit_image"

    @classmethod
    def get_description(cls) -> str:
        base_desc = (
            "Edits an existing image based on a textual description (prompt)"
            "A mask can be provided to specify the exact area to edit (inpainting). "
            "Saves the edited image to the specified local file path and returns the path."
        )
        suffix = _get_model_description_suffix(cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)
        return f"{base_desc}{suffix}"

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
                name="input_images",
                param_type=ParameterType.STRING,
                description=(
                    "A comma-separated string of image locations (URLs or file paths) to be edited. Logic for providing this:\n"
                    "1. **Has Context & Image IN Context:** OMIT.\n"
                    "2. **Has Context & Image NOT in Context:** PROVIDE.\n"
                    "3. **No Context & Supports Input:** PROVIDE.\n"
                    "4. **No Context & No Input Support:** OMIT."
                ),
                required=False
            ),
            ParameterDefinition(
                name="output_file_path",
                param_type=ParameterType.STRING,
                description=(
                    "Required. The local file path (relative to workspace) where the edited image should be saved. "
                    "Example: 'assets/images/edited_result.png'"
                ),
                required=True
            ),
            ParameterDefinition(
                name="mask_image",
                param_type=ParameterType.STRING,
                description=(
                    "Optional. Path or URL to a mask image (PNG) for inpainting. "
                    "Transparent areas are regenerated; opaque areas stay unchanged."
                ),
                required=False
            ),
        ]
        return _build_dynamic_image_schema(base_params, cls.MODEL_ENV_VAR, cls.DEFAULT_MODEL)

    async def _execute(
        self,
        context,
        prompt: str,
        output_file_path: str,
        input_images: Optional[str] = None,
        generation_config: Optional[dict] = None,
        mask_image: Optional[str] = None,
    ) -> Any:
        # 1. Resolve Model ID
        if not self._model_identifier:
            self._model_identifier = _get_configured_model_identifier(self.MODEL_ENV_VAR, self.DEFAULT_MODEL)

        logger.info(f"edit_image executing with configured model '{self._model_identifier}' for agent '{context.agent_id}'.")

        # 2. Obtain Shared Client (Scoped to Agent ID)
        if self._client is None:
            self._client = _SharedImageClientManager.get_client(context.agent_id, self._model_identifier)

        # 3. Process Inputs
        urls_list = []
        if input_images:
             urls_list = [url.strip() for url in input_images.split(',') if url.strip()]
        
        # 4. Execute Edit
        # Note: If urls_list is empty, we still call edit_image.
        # Conversational clients will interpret this as a text-only follow-up.
        # Stateless API clients may throw an error if they enforce input images, which is expected behavior.
        response = await self._client.edit_image(
            prompt=prompt,
            input_image_urls=urls_list,
            mask_url=mask_image,
            generation_config=generation_config
        )

        if not response.image_urls:
            raise ValueError("Image editing failed to return any image URLs.")

        if not output_file_path:
            raise ValueError("output_file_path is required but was not provided.")

        first_url = response.image_urls[0]
        
        # 5. Save to File
        resolved_path = resolve_safe_path(output_file_path, _get_workspace_root(context))
        await download_file_from_url(first_url, resolved_path)

        return {"file_path": str(resolved_path)}

    async def cleanup(self) -> None:
        if self._client and self._model_identifier and self.agent_id:
            await _SharedImageClientManager.release_client(self.agent_id, self._model_identifier)
            self._client = None
