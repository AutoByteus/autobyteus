import pytest
from autobyteus.llm.llm_factory import LLMFactory
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def initialize_llm_factory():
    """Pytest fixture to initialize LLM factory before running integration tests"""
    logger.info("Initializing LLM factory for integration tests")
    LLMFactory.ensure_initialized()
    logger.debug("LLM factory initialization completed")
