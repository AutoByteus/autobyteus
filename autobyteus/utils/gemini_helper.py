import os
import logging
from google import genai

logger = logging.getLogger(__name__)

def initialize_gemini_client() -> genai.Client:
    """
    Initializes the Google GenAI Client based on available environment variables.
    Supports both Vertex AI (GCP) and AI Studio (API Key) modes.
    
    Priority:
    1. Vertex AI (requires VERTEX_AI_PROJECT and VERTEX_AI_LOCATION)
    2. AI Studio (requires GEMINI_API_KEY)
    
    Returns:
        genai.Client: Configured Google GenAI client.
        
    Raises:
        ValueError: If neither configuration set is found.
    """
    # 1. Try Vertex AI Configuration
    project = os.environ.get("VERTEX_AI_PROJECT")
    location = os.environ.get("VERTEX_AI_LOCATION")
    
    if project and location:
        logger.info(f"Initializing Gemini Client in Vertex AI mode (Project: {project}, Location: {location})")
        # Vertex AI uses ADC (Application Default Credentials), so no explicit key is passed here.
        # Ensure 'gcloud auth application-default login' has been run or GOOGLE_APPLICATION_CREDENTIALS is set.
        return genai.Client(vertexai=True, project=project, location=location)

    # 2. Try AI Studio Configuration (API Key)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        logger.info("Initializing Gemini Client in AI Studio mode.")
        return genai.Client(api_key=api_key)

    # 3. Fallback / Error
    error_msg = (
        "Failed to initialize Gemini Client: Missing configuration. "
        "Please set 'GEMINI_API_KEY' for AI Studio mode, OR set both "
        "'VERTEX_AI_PROJECT' and 'VERTEX_AI_LOCATION' for Vertex AI mode."
    )
    logger.error(error_msg)
    raise ValueError(error_msg)
