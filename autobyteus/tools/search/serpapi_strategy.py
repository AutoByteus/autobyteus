import os
import logging
import aiohttp
from typing import Dict, Any, Optional

from .base_strategy import SearchStrategy

logger = logging.getLogger(__name__)

class SerpApiSearchStrategy(SearchStrategy):
    """
    A search strategy that uses the SerpApi.com API.
    """
    API_URL = "https://serpapi.com/search.json"

    def __init__(self):
        self.api_key: Optional[str] = os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SerpApiSearchStrategy requires the 'SERPAPI_API_KEY' environment variable to be set.")
        logger.debug("SerpApiSearchStrategy initialized.")

    def _format_results(self, data: Dict[str, Any]) -> str:
        """Formats the JSON response from SerpApi into a clean string for an LLM."""
        if "organic_results" not in data or not data["organic_results"]:
            return "No relevant information found for the query via SerpApi."

        results = data["organic_results"]
        results_str = "\n".join(
            f"{i+1}. {result.get('title', 'No Title')}\n"
            f"   Link: {result.get('link', 'No Link')}\n"
            f"   Snippet: {result.get('snippet', 'No Snippet')}"
            for i, result in enumerate(results)
        )
        
        return f"Search Results:\n{results_str}"

    async def search(self, query: str, num_results: int) -> str:
        logger.info(f"Executing search with SerpApi strategy for query: '{query}'")
        
        params = {
            'api_key': self.api_key,
            'engine': 'google',
            'q': query,
            'num': num_results
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"SerpApi API returned a non-200 status code: {response.status}. "
                            f"Response: {error_text}"
                        )
                        raise RuntimeError(f"SerpApi API request failed with status {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during SerpApi API call: {e}", exc_info=True)
            raise RuntimeError(f"A network error occurred during SerpApi search: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in SerpApi strategy: {e}", exc_info=True)
            raise
