import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Union

import aiohttp

from .base_strategy import SearchStrategy

logger = logging.getLogger(__name__)


JsonPathSegment = Union[str, int]


class VertexAISearchStrategy(SearchStrategy):
    """A search strategy that uses Vertex AI Search `searchLite`."""

    API_BASE_URL = "https://discoveryengine.googleapis.com/v1alpha"

    def __init__(self):
        self.api_key: Optional[str] = os.getenv("VERTEX_AI_SEARCH_API_KEY")
        self.serving_config: Optional[str] = os.getenv("VERTEX_AI_SEARCH_SERVING_CONFIG")
        if not self.api_key or not self.serving_config:
            raise ValueError(
                "VertexAISearchStrategy requires both 'VERTEX_AI_SEARCH_API_KEY' and "
                "'VERTEX_AI_SEARCH_SERVING_CONFIG' environment variables to be set."
            )

        self.serving_config = self.serving_config.strip().lstrip("/")
        if "/servingConfigs/" not in self.serving_config:
            raise ValueError(
                "VERTEX_AI_SEARCH_SERVING_CONFIG must include a full serving config path like "
                "'projects/{project}/locations/{location}/collections/{collection}/engines/{engine}/servingConfigs/{servingConfig}'."
            )

    @staticmethod
    def _read_path(source: Any, path: Sequence[JsonPathSegment]) -> Any:
        current = source
        for segment in path:
            if isinstance(current, list):
                try:
                    index = int(segment)
                except (TypeError, ValueError):
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue

            if not isinstance(current, dict):
                return None
            current = current.get(str(segment))
        return current

    @staticmethod
    def _coerce_text(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None

    @classmethod
    def _pick_text(cls, source: Any, candidates: Sequence[Sequence[JsonPathSegment]]) -> Optional[str]:
        for path in candidates:
            value = cls._coerce_text(cls._read_path(source, path))
            if value:
                return value
        return None

    def _format_results(self, data: Dict[str, Any]) -> str:
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return "No relevant information found for the query via Vertex AI Search."

        lines: List[str] = []
        for i, result in enumerate(results):
            title = self._pick_text(
                result,
                [
                    ["document", "derivedStructData", "title"],
                    ["document", "structData", "title"],
                    ["chunk", "derivedStructData", "title"],
                    ["chunk", "structData", "title"],
                    ["document", "id"],
                    ["document", "name"],
                ],
            ) or "No Title"

            link = self._pick_text(
                result,
                [
                    ["document", "derivedStructData", "link"],
                    ["document", "derivedStructData", "url"],
                    ["document", "structData", "link"],
                    ["document", "structData", "url"],
                    ["chunk", "derivedStructData", "link"],
                    ["chunk", "derivedStructData", "url"],
                    ["chunk", "structData", "link"],
                    ["chunk", "structData", "url"],
                    ["document", "name"],
                ],
            ) or "No Link"

            snippet = self._pick_text(
                result,
                [
                    ["document", "derivedStructData", "snippet"],
                    ["document", "derivedStructData", "description"],
                    ["document", "structData", "snippet"],
                    ["document", "structData", "description"],
                    ["chunk", "content"],
                    ["snippetInfo", "snippet"],
                    ["summary"],
                ],
            ) or "No Snippet"

            lines.append(f"{i + 1}. {title}\n   Link: {link}\n   Snippet: {snippet}")

        return f"Search Results:\n{chr(10).join(lines)}"

    async def search(self, query: str, num_results: int) -> str:
        logger.info(f"Executing search with Vertex AI Search strategy for query: '{query}'")

        url = f"{self.API_BASE_URL}/{self.serving_config}:searchLite"
        payload = {"query": query, "pageSize": num_results}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params={"key": self.api_key}, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_results(data)

                    error_text = await response.text()
                    logger.error(
                        "Vertex AI Search API returned a non-200 status code: %s. Response: %s",
                        response.status,
                        error_text,
                    )
                    raise RuntimeError(
                        f"Vertex AI Search API request failed with status {response.status}: {error_text}"
                    )
        except aiohttp.ClientError as exc:
            logger.error("Network error during Vertex AI Search API call: %s", exc, exc_info=True)
            raise RuntimeError(f"A network error occurred during Vertex AI Search: {exc}") from exc
        except Exception as exc:
            logger.error("An unexpected error occurred in Vertex AI Search strategy: %s", exc, exc_info=True)
            raise
