import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_strategy import SearchStrategy

logger = logging.getLogger(__name__)

class SearchClient:
    """
    A client that uses a configured search strategy to perform searches.
    This acts as the 'Context' in the Strategy pattern.
    """
    def __init__(self, strategy: 'SearchStrategy'):
        if not strategy:
            raise ValueError("SearchClient must be initialized with a valid SearchStrategy.")
        self._strategy = strategy
        logger.debug(f"SearchClient initialized with strategy: {type(strategy).__name__}")

    async def search(self, query: str, num_results: int) -> str:
        """
        Delegates the search operation to the configured strategy.
        """
        return await self._strategy.search(query, num_results)
