import os
import logging
from typing import Optional

from autobyteus.utils.singleton import SingletonMeta
from .providers import SearchProvider
from .client import SearchClient
from .serper_strategy import SerperSearchStrategy
from .serpapi_strategy import SerpApiSearchStrategy
from .google_cse_strategy import GoogleCSESearchStrategy

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
        google_api_key = os.getenv("GOOGLE_CSE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        is_serper_configured = bool(serper_key)
        is_serpapi_configured = bool(serpapi_key)
        is_google_cse_configured = bool(google_api_key and google_cse_id)
        
        strategy = None

        if provider_name == SearchProvider.GOOGLE_CSE:
            if is_google_cse_configured:
                logger.info("DEFAULT_SEARCH_PROVIDER is 'google_cse', using Google CSE strategy.")
                strategy = GoogleCSESearchStrategy()
            else:
                raise ValueError("DEFAULT_SEARCH_PROVIDER is 'google_cse', but Google CSE is not configured. "
                                 "Set GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID.")

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

        elif is_google_cse_configured:
            logger.info("Neither Serper nor SerpApi are configured, falling back to available Google CSE strategy.")
            strategy = GoogleCSESearchStrategy()
        
        else:
            raise ValueError("No search provider is configured. Please set either SERPER_API_KEY, SERPAPI_API_KEY, "
                             "or both GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables.")

        self._instance = SearchClient(strategy=strategy)
        return self._instance
