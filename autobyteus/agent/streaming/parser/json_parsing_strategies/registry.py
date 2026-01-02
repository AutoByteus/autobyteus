"""Provider-aware JSON tool parsing profiles."""
from dataclasses import dataclass
from typing import List, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.tool_call_format import resolve_tool_call_format

from .base import JsonToolParsingStrategy
from .default import DefaultJsonToolParsingStrategy
from .gemini import GeminiJsonToolParsingStrategy
from .openai import OpenAiJsonToolParsingStrategy


@dataclass(frozen=True)
class JsonToolParsingProfile:
    parser: JsonToolParsingStrategy
    signature_patterns: List[str]


OPENAI_JSON_PATTERNS = [
    '{"tool":',
    '{"tool_calls":',
    '{"tools":',
    '{"function":',
    '[{"tool":',
    '[{"function":',
]

GEMINI_JSON_PATTERNS = [
    '{"name":',
    '[{"name":',
]

DEFAULT_JSON_PATTERNS = [
    '{"tool":',
    '{"function":',
]


OPENAI_PROFILE = JsonToolParsingProfile(
    parser=OpenAiJsonToolParsingStrategy(),
    signature_patterns=OPENAI_JSON_PATTERNS,
)

GEMINI_PROFILE = JsonToolParsingProfile(
    parser=GeminiJsonToolParsingStrategy(),
    signature_patterns=GEMINI_JSON_PATTERNS,
)

DEFAULT_PROFILE = JsonToolParsingProfile(
    parser=DefaultJsonToolParsingStrategy(),
    signature_patterns=DEFAULT_JSON_PATTERNS,
)


OPENAI_LIKE_PROVIDERS = {
    LLMProvider.OPENAI,
    LLMProvider.MISTRAL,
    LLMProvider.DEEPSEEK,
    LLMProvider.GROK,
}


def get_json_tool_parsing_profile(provider: Optional[LLMProvider]) -> JsonToolParsingProfile:
    """Return the JSON tool parsing profile for a provider, honoring overrides."""
    override = resolve_tool_call_format()
    if override == "json":
        return DEFAULT_PROFILE

    if provider == LLMProvider.GEMINI:
        return GEMINI_PROFILE
    if provider in OPENAI_LIKE_PROVIDERS:
        return OPENAI_PROFILE

    return DEFAULT_PROFILE
