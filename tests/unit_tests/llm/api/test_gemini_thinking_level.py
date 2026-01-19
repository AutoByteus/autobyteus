# file: autobyteus/tests/unit_tests/llm/api/test_gemini_thinking_level.py
"""
Unit tests for GeminiLLM thinking_level configuration.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from autobyteus.llm.utils.llm_config import LLMConfig


class TestGeminiThinkingLevel:
    """Tests for thinking_level -> thinking_budget translation."""
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock the Gemini client initialization."""
        with patch('autobyteus.llm.api.gemini_llm.initialize_gemini_client_with_runtime') as mock:
            mock_client = MagicMock()
            mock_client.aio = MagicMock()
            mock.return_value = (mock_client, {"runtime": "test"})
            yield mock

    def test_thinking_level_minimal_returns_zero_budget(self, mock_gemini_client):
        """thinking_level='minimal' should return thinking_budget=0."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        mock_llm_class = MagicMock()
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        config = LLMConfig(extra_params={"thinking_level": "minimal"})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 0

    def test_thinking_level_low_returns_1024_budget(self, mock_gemini_client):
        """thinking_level='low' should return thinking_budget=1024."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        config = LLMConfig(extra_params={"thinking_level": "low"})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 1024

    def test_thinking_level_medium_returns_4096_budget(self, mock_gemini_client):
        """thinking_level='medium' should return thinking_budget=4096."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        config = LLMConfig(extra_params={"thinking_level": "medium"})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 4096

    def test_thinking_level_high_returns_16384_budget(self, mock_gemini_client):
        """thinking_level='high' should return thinking_budget=16384."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        config = LLMConfig(extra_params={"thinking_level": "high"})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 16384

    def test_default_thinking_level_is_minimal(self, mock_gemini_client):
        """When no thinking_level is set, default should be minimal (0)."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        # No thinking_level in extra_params
        config = LLMConfig(extra_params={})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 0

    def test_invalid_thinking_level_falls_back_to_zero(self, mock_gemini_client):
        """Invalid thinking_level should fall back to 0 budget."""
        from autobyteus.llm.api.gemini_llm import GeminiLLM
        from autobyteus.llm.models import LLMModel
        from autobyteus.llm.providers import LLMProvider
        
        model = LLMModel(
            name="gemini-test",
            value="gemini-test-v1",
            provider=LLMProvider.GEMINI,
            llm_class=GeminiLLM,
            canonical_name="gemini-test",
        )
        
        config = LLMConfig(extra_params={"thinking_level": "invalid_level"})
        llm = GeminiLLM(model=model, llm_config=config)
        
        gen_config = llm._get_generation_config()
        
        assert gen_config.thinking_config.thinking_budget == 0
