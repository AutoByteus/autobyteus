import pytest
import os

@pytest.fixture(autouse=True)
def setup_and_teardown_redis():
    """
    This fixture sets up a test Redis database before the test and restores the original one after the test.
    """
    # Save old configurations
    old_host = os.environ.get('REDIS_HOST', 'localhost')
    old_port = os.environ.get('REDIS_PORT', '6379')
    old_db = os.environ.get('REDIS_DB', '0')

    # Set new configurations with a different db for testing
    os.environ['REDIS_HOST'] = old_host
    os.environ['REDIS_PORT'] = old_port
    os.environ['REDIS_DB'] = str(int(old_db) + 1)  # Make sure to choose an unused db

    yield  # This is where the testing happens

    # After the test, restore the old configurations
    os.environ['REDIS_HOST'] = old_host
    os.environ['REDIS_PORT'] = old_port
    os.environ['REDIS_DB'] = old_db