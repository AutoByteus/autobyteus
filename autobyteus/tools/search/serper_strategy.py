import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional

from .base_strategy import SearchStrategy

logger = logging.getLogger(__name__)

class SerperSearchStrategy(SearchStrategy):
    """
    A search strategy that uses the Serper.dev API.
    """
    API_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key: Optional[str] = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SerperSearchStrategy requires the 'SERPER_API_KEY' environment variable to be set.")
        logger.debug("SerperSearchStrategy initialized.")

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
            return "No relevant information found for the query via Serper."

        return "\n\n---\n\n".join(summary_parts)

    async def search(self, query: str, num_results: int) -> str:
        logger.info(f"Executing search with Serper strategy for query: '{query}'")
        
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
                        raise RuntimeError(f"Serper API request failed with status {response.status}: {error_text}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error during Serper API call: {e}", exc_info=True)
            raise RuntimeError(f"A network error occurred during Serper search: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred in Serper strategy: {e}", exc_info=True)
            raise
