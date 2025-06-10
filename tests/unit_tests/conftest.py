# file: autobyteus/tests/unit_tests/conftest.py
import pytest
import logging

logger = logging.getLogger(__name__)

# This file can be used for fixtures that are shared across all unit tests,
# but for now, the more specific conftest files in subdirectories are sufficient.
# The LLMFactory fixture has been removed as it's no longer a dependency for agent creation.
