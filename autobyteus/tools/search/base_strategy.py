from abc import ABC, abstractmethod
from typing import Dict, Any

class SearchStrategy(ABC):
    """
    Abstract base class for a search provider strategy.
    Defines the common interface for performing a search and formatting results.
    """

    @abstractmethod
    async def search(self, query: str, num_results: int) -> str:
        """
        Executes a search query against a specific provider.

        Args:
            query: The search query string.
            num_results: The desired number of organic search results.

        Returns:
            A formatted string summarizing the search results, suitable for an LLM.
        """
        pass

    @abstractmethod
    def _format_results(self, data: Dict[str, Any]) -> str:
        """
        Formats the raw JSON response from the search API into a clean string.

        Args:
            data: The JSON data from the API response.

        Returns:
            A formatted summary string.
        """
        pass
