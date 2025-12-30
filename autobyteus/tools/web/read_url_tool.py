import logging
import aiohttp
from typing import Optional, TYPE_CHECKING
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ReadUrl(BaseTool):
    """
    Lightweight URL content reader that fetches web page content using aiohttp.
    Optimized for fast, efficient reading of static content by extracting pure text.
    """
    CATEGORY = ToolCategory.WEB

    @classmethod
    def get_name(cls) -> str:
        return "read_url"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Reads the content of a specific URL using a lightweight HTTP client. "
            "Faster and more efficient than using a browser tool for static pages. "
            "Returns cleaned text content optimized for reading."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The URL of the webpage to read.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="output_format",
            param_type=ParameterType.STRING,
            description="The desired output format: 'text' (default) or 'html'. 'text' returns cleaned text content, 'html' returns cleaned HTML.",
            required=False,
            default_value="text",
            enum_values=["text", "html"]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, output_format: str = "text") -> str:
        logger.info(f"Executing read_url for agent {context.agent_id} with URL: '{url}'")

        try:
            async with aiohttp.ClientSession() as session:
                # aiohttp handles redirects by default (up to 10)
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        error_msg = f"Failed to fetch content from {url}. Status code: {response.status}"
                        logger.error(error_msg)
                        return error_msg
                    
                    html_content = await response.text()
            
            # Use appropriate cleaning mode based on requested format
            mode = CleaningMode.TEXT_CONTENT_FOCUSED if output_format == "text" else CleaningMode.THOROUGH
            cleaned_content = clean(html_content, mode=mode)
            
            if not cleaned_content.strip():
                return f"Successfully fetched content from {url}, but the cleaned result was empty."
                
            return cleaned_content

        except aiohttp.ClientError as e:
            logger.error(f"Network error reading URL '{url}': {e}", exc_info=True)
            return f"Error reading URL '{url}': Network error ({str(e)})"
        except Exception as e:
            logger.error(f"Unexpected error reading URL '{url}': {e}", exc_info=True)
            return f"Error reading URL '{url}': {str(e)}"
