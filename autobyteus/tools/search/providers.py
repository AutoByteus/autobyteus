from enum import Enum

class SearchProvider(str, Enum):
    """Enumerates the supported search providers."""
    SERPER = "serper"
    SERPAPI = "serpapi"
    VERTEX_AI_SEARCH = "vertex_ai_search"

    def __str__(self) -> str:
        return self.value
