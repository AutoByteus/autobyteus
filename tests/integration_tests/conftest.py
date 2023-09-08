import pytest
from autobyteus.config import config

@pytest.fixture(autouse=True)
def setup_and_teardown_redis():
    """
    This fixture sets up a test Redis database before the test and restores the original one after the test.
    """
    # Save old configurations
    old_host = config.get('REDIS_HOST', default='localhost')
    old_port = config.get('REDIS_PORT', default=6379)
    old_db = config.get('REDIS_DB', default=0)

    # Set new configurations with a different db for testing
    config.set('REDIS_HOST', old_host)
    config.set('REDIS_PORT', old_port)
    config.set('REDIS_DB', old_db + 1)  # Make sure to choose an unused db

    yield  # This is where the testing happens

    # After the test, restore the old configurations
    config.set('REDIS_HOST', old_host)
    config.set('REDIS_PORT', old_port)
    config.set('REDIS_DB', old_db)
