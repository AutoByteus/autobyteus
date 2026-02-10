import os
import logging
from typing import Optional

from autobyteus.utils.singleton import SingletonMeta
from .providers import SearchProvider
from .client import SearchClient
from .serper_strategy import SerperSearchStrategy
from .serpapi_strategy import SerpApiSearchStrategy
from .vertex_ai_search_strategy import VertexAISearchStrategy

logger = logging.getLogger(__name__)

class SearchClientFactory(metaclass=SingletonMeta):
    """
    Factory for creating a SearchClient with the appropriate strategy
    based on environment variable configuration.
    """
    _instance: Optional[SearchClient] = None

    def create_search_client(self) -> SearchClient:
        """
        Creates and returns a singleton instance of the SearchClient, configured
        with the appropriate search strategy.
        """
        if self._instance:
            return self._instance

        provider_name = os.getenv("DEFAULT_SEARCH_PROVIDER", "").lower()
        
        serper_key = os.getenv("SERPER_API_KEY")
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        vertex_api_key = os.getenv("VERTEX_AI_SEARCH_API_KEY")
        vertex_serving_config = os.getenv("VERTEX_AI_SEARCH_SERVING_CONFIG")
        
        is_serper_configured = bool(serper_key)
        is_serpapi_configured = bool(serpapi_key)
        is_vertex_ai_search_configured = bool(vertex_api_key and vertex_serving_config)
        
        strategy = None

        if provider_name == "google_cse":
            raise ValueError(
                "DEFAULT_SEARCH_PROVIDER 'google_cse' is no longer supported. "
                "Use 'serper', 'serpapi', or 'vertex_ai_search'."
            )

        elif provider_name == SearchProvider.VERTEX_AI_SEARCH:
            if is_vertex_ai_search_configured:
                logger.info("DEFAULT_SEARCH_PROVIDER is 'vertex_ai_search', using Vertex AI Search strategy.")
                strategy = VertexAISearchStrategy()
            else:
                raise ValueError(
                    "DEFAULT_SEARCH_PROVIDER is 'vertex_ai_search', but Vertex AI Search is not configured. "
                    "Set VERTEX_AI_SEARCH_API_KEY and VERTEX_AI_SEARCH_SERVING_CONFIG."
                )

        elif provider_name == SearchProvider.SERPAPI:
            if is_serpapi_configured:
                logger.info("DEFAULT_SEARCH_PROVIDER is 'serpapi', using SerpApi strategy.")
                strategy = SerpApiSearchStrategy()
            else:
                raise ValueError("DEFAULT_SEARCH_PROVIDER is 'serpapi', but SerpApi is not configured. "
                                 "Set SERPAPI_API_KEY.")
        
        # Default to Serper if explicitly set, or if not set and Serper is available.
        # This handles the case where multiple providers are configured but no provider is specified.
        elif provider_name == SearchProvider.SERPER or is_serper_configured:
            if is_serper_configured:
                logger.info("Using Serper search strategy (either as default or as first fallback).")
                strategy = SerperSearchStrategy()
            else:
                # This branch is only taken if provider_name is 'serper' but it's not configured.
                raise ValueError("DEFAULT_SEARCH_PROVIDER is 'serper', but Serper is not configured. Set SERPER_API_KEY.")

        elif is_serpapi_configured:
            logger.info("Serper not configured, falling back to available SerpApi strategy.")
            strategy = SerpApiSearchStrategy()

        elif is_vertex_ai_search_configured:
            logger.info("Neither Serper nor SerpApi are configured, falling back to available Vertex AI Search strategy.")
            strategy = VertexAISearchStrategy()
        
        else:
            raise ValueError("No search provider is configured. Please set either SERPER_API_KEY, SERPAPI_API_KEY, "
                             "or both VERTEX_AI_SEARCH_API_KEY and VERTEX_AI_SEARCH_SERVING_CONFIG environment variables.")

        self._instance = SearchClient(strategy=strategy)
        return self._instance
