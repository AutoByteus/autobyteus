import pytest
from autobyteus.multimedia.image import image_client_factory
from autobyteus.multimedia.audio import audio_client_factory
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def initialize_multimedia_factories():
    """
    Pytest fixture to initialize all multimedia client factories before running
    any multimedia-related integration tests.
    """
    logger.info("Initializing ImageClientFactory for integration tests")
    image_client_factory.ensure_initialized()
    logger.debug("ImageClientFactory initialization completed")
    
    logger.info("Initializing AudioClientFactory for integration tests")
    audio_client_factory.ensure_initialized()
    logger.debug("AudioClientFactory initialization completed")
