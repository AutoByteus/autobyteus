import pytest
from autobyteus.multimedia import multimedia_client_factory
import logging

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def initialize_multimedia_factory():
    """
    Pytest fixture to initialize the MultimediaClientFactory before running
    any multimedia-related integration tests.
    """
    logger.info("Initializing MultimediaClientFactory for integration tests")
    multimedia_client_factory.ensure_initialized()
    logger.debug("MultimediaClientFactory initialization completed")
