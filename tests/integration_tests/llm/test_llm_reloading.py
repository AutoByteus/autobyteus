
import pytest
from unittest.mock import MagicMock, patch
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.models import LLMModel, LLMProvider, LLMRuntime
from autobyteus.llm.lmstudio_provider import LMStudioModelProvider
from autobyteus.llm.api.lmstudio_llm import LMStudioLLM

class TestLLMReloading:

    @pytest.fixture(autouse=True)
    def setup_factory(self):
        # Prevent actual discovery from polluting the test state
        with patch('autobyteus.llm.ollama_provider.OllamaModelProvider.discover_and_register'), \
             patch('autobyteus.llm.lmstudio_provider.LMStudioModelProvider.discover_and_register'), \
             patch('autobyteus.llm.autobyteus_provider.AutobyteusModelProvider.discover_and_register'):
            LLMFactory.reinitialize()
        yield
        LLMFactory.reinitialize()

    def test_reload_models_atomic_success(self):
        """
        Verifies that reload_models correctly replaces old models with new ones 
        when the fetch (get_models) is successful.
        """
        # 1. Setup initial state: LMStudio has 1 model "old-model"
        initial_model = LLMModel(
            name="old-model", value="old-model", provider=LLMProvider.LMSTUDIO,
            llm_class=LMStudioLLM, canonical_name="old", runtime=LLMRuntime.LMSTUDIO, host_url="http://local"
        )
        LLMFactory.register_model(initial_model)
        
        assert len(LLMFactory.list_models_by_provider(LLMProvider.LMSTUDIO)) == 1

        # 2. Mock get_models to return 2 NEW models
        new_model_1 = LLMModel(
            name="new-model-1", value="new-model-1", provider=LLMProvider.LMSTUDIO,
            llm_class=LMStudioLLM, canonical_name="new1", runtime=LLMRuntime.LMSTUDIO, host_url="http://local"
        )
        new_model_2 = LLMModel(
            name="new-model-2", value="new-model-2", provider=LLMProvider.LMSTUDIO,
            llm_class=LMStudioLLM, canonical_name="new2", runtime=LLMRuntime.LMSTUDIO, host_url="http://local"
        )

        with patch.object(LMStudioModelProvider, 'get_models', return_value=[new_model_1, new_model_2]) as mock_fetch:
            # 3. Perform Reload
            count = LLMFactory.reload_models(LLMProvider.LMSTUDIO)
            
            # 4. Verify Results
            assert count == 2
            mock_fetch.assert_called_once()
            
            # Old model should be gone, new models present
            current_models = LLMFactory.list_models_by_provider(LLMProvider.LMSTUDIO)
            current_ids = [m.model_identifier for m in current_models]
            
            assert "old-model:lmstudio" not in current_ids # Assuming ID format includes runtime or is unique
            assert new_model_1.model_identifier in current_ids
            assert new_model_2.model_identifier in current_ids

    def test_reload_models_fail_fast_failure(self):
        """
        Verifies that reload_models clears existing models even if the fetch fails (fail fast).
        """
        # 1. Setup initial state
        initial_model = LLMModel(
            name="precious-data", value="precious", provider=LLMProvider.OLLAMA,
            llm_class=LMStudioLLM, canonical_name="precious", runtime=LLMRuntime.OLLAMA, host_url="http://local"
        )
        LLMFactory.register_model(initial_model)
        assert len(LLMFactory.list_models_by_provider(LLMProvider.OLLAMA)) == 1

        # 2. Mock get_models to raise an exception
        # We need to resolve the correct handler class for OLLAMA inside the factory
        # For this test, we can patch the specific provider class involved.
        from autobyteus.llm.ollama_provider import OllamaModelProvider
        
        with patch.object(OllamaModelProvider, 'get_models', side_effect=ConnectionError("Server Down")):
            # 3. Perform Reload
            count = LLMFactory.reload_models(LLMProvider.OLLAMA)
            
            # 4. Verify Results
            assert count == 0 # Should now be 0 because we clear before fetch
            
            # Data should be wiped (Fail Fast)
            current_models = LLMFactory.list_models_by_provider(LLMProvider.OLLAMA)
            assert len(current_models) == 0

    def test_reload_unsupported_provider(self):
        """
        Verifies that reloading an unsupported provider (like OPENAI) does nothing safely.
        """
        # OpenAI models are hardcoded in factory init, so there should be some.
        LLMFactory.ensure_initialized()
        openai_count_initial = len(LLMFactory.list_models_by_provider(LLMProvider.OPENAI))
        assert openai_count_initial > 0

        # Reload
        count = LLMFactory.reload_models(LLMProvider.OPENAI)
        
        # Verify
        assert count == openai_count_initial
        # Also check logs via pytest caplog if needed, but return value is enough for now
