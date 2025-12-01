import os
import logging
from dataclasses import dataclass
from google import genai

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiRuntimeInfo:
    runtime: str  # "vertex" or "api_key"
    project: str | None
    location: str | None

def initialize_gemini_client_with_runtime() -> tuple[genai.Client, GeminiRuntimeInfo]:
    """
    Initializes the Google GenAI Client based on available environment variables.
    Supports both Vertex AI (GCP) and AI Studio (API Key) modes.

    Priority:
    1. Vertex AI (requires VERTEX_AI_PROJECT and VERTEX_AI_LOCATION)
    2. AI Studio (requires GEMINI_API_KEY)

    Returns:
        (client, runtime_info)

    Raises:
        ValueError: If neither configuration set is found.
    """
    # 1. Try Vertex AI Configuration
    project = os.environ.get("VERTEX_AI_PROJECT")
    location = os.environ.get("VERTEX_AI_LOCATION")

    if project and location:
        logger.info(
            f"Initializing Gemini Client in Vertex AI mode (Project: {project}, Location: {location})"
        )
        client = genai.Client(vertexai=True, project=project, location=location)
        return client, GeminiRuntimeInfo(runtime="vertex", project=project, location=location)

    # 2. Try AI Studio Configuration (API Key)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        logger.info("Initializing Gemini Client in AI Studio mode.")
        client = genai.Client(api_key=api_key)
        return client, GeminiRuntimeInfo(runtime="api_key", project=None, location=None)

    # 3. Fallback / Error
    error_msg = (
        "Failed to initialize Gemini Client: Missing configuration. "
        "Please set 'GEMINI_API_KEY' for AI Studio mode, OR set both "
        "'VERTEX_AI_PROJECT' and 'VERTEX_AI_LOCATION' for Vertex AI mode."
    )
    logger.error(error_msg)
    raise ValueError(error_msg)

