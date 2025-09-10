import os
import pytest
import logging
from pathlib import Path
from dotenv import load_dotenv

# --- Eagerly load test environment on import ---
# This logic is executed as soon as pytest imports this conftest.py file during
# its collection phase. This guarantees that environment variables are available
# before any application code (like tool metaclasses) is imported and executed.
# This solves the initialization order problem for the test suite.
project_root = Path(__file__).parent.parent
env_test_path = project_root / '.env.test'

if not env_test_path.exists():
    # This is a critical failure. The test suite cannot run without its configuration.
    raise FileNotFoundError(f"CRITICAL: Test environment file not found at '{env_test_path}'. Tests cannot proceed.")

# Load the environment variables from .env.test, overriding any existing system variables.
load_dotenv(env_test_path, override=True)
logging.info(f"Successfully loaded test environment from {env_test_path}")

def pytest_configure(config):
    # Create a custom logger
    logger = logging.getLogger('autobyteus')
    logger.setLevel(logging.DEBUG)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    logger.addHandler(ch)

@pytest.fixture(scope='session', autouse=True)
def configure_logging():
    # This fixture will be automatically used by all tests
    pass
