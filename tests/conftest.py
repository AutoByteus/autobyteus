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

@pytest.fixture(scope="session", autouse=True)
def configure_logging_for_tests():
    """
    Session-wide fixture to configure logging levels for tests.
    This suppresses noisy INFO and DEBUG logs from specific libraries.
    """
    # Set the logging level for 'watchdog' to WARNING to hide verbose file event logs
    logging.getLogger('watchdog').setLevel(logging.WARNING)
    
    # You can also control your application's log level during tests
    logging.getLogger('autobyteus_server').setLevel(logging.WARNING)
