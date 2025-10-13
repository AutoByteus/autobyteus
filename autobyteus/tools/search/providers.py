from enum import Enum

class SearchProvider(str, Enum):
    """Enumerates the supported search providers."""
    SERPER = "serper"
    GOOGLE_CSE = "google_cse"
    SERPAPI = "serpapi"

    def __str__(self) -> str:
        return self.value
