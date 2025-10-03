import os
import json
import logging
import aiohttp
from typing import Optional, TYPE_CHECKING, Any, Dict, List

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class GoogleSearch(BaseTool):
    """
    Performs a Google search using the Serper.dev API and returns a structured summary of the results.
    This tool requires a Serper API key, which should be set in the SERPER_API_KEY environment variable.
    """
    CATEGORY = ToolCategory.WEB
    API_URL = "https://google.serper.dev/search"

    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        self.api_key: Optional[str] = None
        
        if config:
            self.api_key = config.get('api_key')
        
        if not self.api_key:
            self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise ValueError(
                "GoogleSearch tool requires a Serper API key. "
                "Please provide it via the 'api_key' config parameter or set the 'SERPER_API_KEY' environment variable."
            )
        logger.debug("GoogleSearch (API-based) tool initialized.")
    
    @classmethod
    def get_name(cls) -> str:
        return "GoogleSearch"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Searches Google for a given query using the Serper API. "
            "Returns a concise, structured summary of search results, including direct answers and top organic links."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="query",
            param_type=ParameterType.STRING,
            description="The search query string.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="num_results",
            param_type=ParameterType.INTEGER,
            description="The number of organic search results to return.",
            required=False,
            default_value=5,
            min_value=1,
            max_value=10
        ))
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="api_key",
            param_type=ParameterType.STRING,
            description="The API key for the Serper.dev service. Overrides the SERPER_API_KEY environment variable.",
            required=False
        ))
        return schema

    def _format_results(self, data: Dict[str, Any]) -> str:
        """Formats the JSON response from Serper into a clean string for an LLM."""
        summary_parts = []
        
        # 1. Answer Box (most important for direct questions)
        if "answerBox" in data:
            answer_box = data["answerBox"]
            title = answer_box.get("title", "")
            snippet = answer_box.get("snippet") or answer_box.get("answer")
            summary_parts.append(f"Direct Answer for '{title}':\n{snippet}")

        # 2. Knowledge Graph (for entity information)
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            title = kg.get("title", "")
            description = kg.get("description")
            summary_parts.append(f"Summary for '{title}':\n{description}")

        # 3. Organic Results (the main search links)
        if "organic" in data and data["organic"]:
            organic_results = data["organic"]
            results_str = "\n".join(
                f"{i+1}. {result.get('title', 'No Title')}\n"
                f"   Link: {result.get('link', 'No Link')}\n"
                f"   Snippet: {result.get('snippet', 'No Snippet')}"
                for i, result in enumerate(organic_results)
            )
            summary_parts.append(f"Search Results:\n{results_str}")
        
        if not summary_parts:
            return "No relevant information found for the query."

        return "\n\n---\n\n".join(summary_parts)


    async def _execute(self, context: 'AgentContext', query: str, num_results: int = 5) -> str:
        logger.info(f"Executing GoogleSearch (API) for agent {context.agent_id} with query: '{query}'")
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "q": query,
            "num": num_results
        })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, headers=headers, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Serper API returned a non-200 status code: {response.status}. "
                            f"Response: {error_text}"
                        )
                        raise RuntimeError(f"API request failed with status {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during GoogleSearch API call: {e}", exc_info=True)
            raise RuntimeError(f"A network error occurred: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in GoogleSearch tool: {e}", exc_info=True)
            raise
