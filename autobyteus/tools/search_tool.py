import logging
from typing import Optional, TYPE_CHECKING

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.search import SearchClientFactory, SearchClient

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


class Search(BaseTool):
    """
    Performs a web search using a configurable backend provider (e.g., Serper.dev, Google CSE).
    Returns a structured summary of the results.
    Configuration is managed via environment variables (see SearchClientFactory for details).
    """
    CATEGORY = ToolCategory.WEB

    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        try:
            factory = SearchClientFactory()
            self.search_client: SearchClient = factory.create_search_client()
        except ValueError as e:
            logger.error(f"Failed to initialize search_web tool: {e}", exc_info=True)
            # Re-raise to prevent tool from being used in a misconfigured state.
            raise RuntimeError(
                "Could not initialize Search tool. Please check your search provider configuration. "
                f"Error: {e}"
            )
            logger.debug("search_web tool initialized with a configured search client.")
    
    @classmethod
    def get_name(cls) -> str:
        return "search_web"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Searches the web for a given query using the configured search provider. "
            "Returns a concise, structured summary of search results, including direct answers (if available) and top organic links."
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
        # Configuration is now handled by the factory via environment variables,
        # so this tool no longer has instance-specific configuration.
        return None

    async def _execute(self, context: 'AgentContext', query: str, num_results: int = 5) -> str:
        logger.info(f"Executing search_web for agent {context.agent_id} with query: '{query}'")
        
        try:
            return await self.search_client.search(query=query, num_results=num_results)
        except Exception as e:
            logger.error(f"An unexpected error occurred in search_web execution: {e}", exc_info=True)
            # Re-raise to ensure the agent is aware of the failure.
            raise
