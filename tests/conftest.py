import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

def load_test_env():
    """Load test environment variables from .env.test file"""
    project_root = Path(__file__).parent.parent
    env_test_path = project_root / '.env.test'
    
    if not env_test_path.exists():
        raise FileNotFoundError(f"Test environment file not found: {env_test_path}")
    
    load_dotenv(env_test_path)

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Session-wide fixture to set and restore test environment variables"""
    original_env = os.environ.copy()
    
    load_test_env()
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)
