import os
import logging
import aiohttp
from typing import Dict, Any, Optional

from .base_strategy import SearchStrategy

logger = logging.getLogger(__name__)

class GoogleCSESearchStrategy(SearchStrategy):
    """
    A search strategy that uses the official Google Custom Search Engine (CSE) API.
    """
    API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key: Optional[str] = os.getenv("GOOGLE_CSE_API_KEY")
        self.cse_id: Optional[str] = os.getenv("GOOGLE_CSE_ID")
        if not self.api_key or not self.cse_id:
            raise ValueError(
                "GoogleCSESearchStrategy requires both 'GOOGLE_CSE_API_KEY' and 'GOOGLE_CSE_ID' environment variables to be set."
            )
        logger.debug("GoogleCSESearchStrategy initialized.")

    def _format_results(self, data: Dict[str, Any]) -> str:
        """Formats the JSON response from Google CSE API into a clean string for an LLM."""
        if "items" not in data or not data["items"]:
            return "No relevant information found for the query via Google CSE."

        results = data["items"]
        results_str = "\n".join(
            f"{i+1}. {result.get('title', 'No Title')}\n"
            f"   Link: {result.get('link', 'No Link')}\n"
            f"   Snippet: {result.get('snippet', 'No Snippet')}"
            for i, result in enumerate(results)
        )
        
        return f"Search Results:\n{results_str}"

    async def search(self, query: str, num_results: int) -> str:
        logger.info(f"Executing search with Google CSE strategy for query: '{query}'")
        
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
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
                            f"Google CSE API returned a non-200 status code: {response.status}. "
                            f"Response: {error_text}"
                        )
                        raise RuntimeError(f"Google CSE API request failed with status {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Google CSE API call: {e}", exc_info=True)
            raise RuntimeError(f"A network error occurred during Google CSE search: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in Google CSE strategy: {e}", exc_info=True)
            raise
