import pytest
from autobyteus.llm.autobyteus_provider import AutobyteusModelProvider
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.models import LLMProvider

@pytest.mark.asyncio
async def test_successful_model_registration():
    """Test successful discovery and registration of models from live server"""
    # Clear previous registrations
    LLMFactory._models_by_provider.clear()
    
    # Execute discovery and registration
    AutobyteusModelProvider.discover_and_register()
    
    # Verify registration
    registered_models = LLMFactory.get_models_for_provider(LLMProvider.OPENAI)
    
    
    # Basic validation of first registered model
    model = registered_models[0]
    assert model.name, "Model should have a name"
    assert model.value, "Model should have a value"
    assert model.provider == LLMProvider.OPENAI
    assert model.llm_class.__name__ == "AutobyteusLLM"

@pytest.mark.asyncio
async def test_no_models_available():
    """Test handling when server returns no models"""
    # Clear previous registrations
    LLMFactory._models_by_provider.clear()
    
    # Execute discovery (assuming empty response would come from server)
    await AutobyteusModelProvider.discover_and_register()
    
    # Verify no models registered
    assert len(LLMFactory.get_models_for_provider(LLMProvider.AUTOBYTEUS)) == 0

@pytest.mark.asyncio
async def test_preserve_existing_registrations_on_failure(monkeypatch):
    """Test existing registrations are preserved when discovery fails"""
    # Add dummy registration
    dummy_model = LLMProvider.AUTOBYTEUS.create_model(
        name="Backup Model",
        value="backup-model",
        config={}
    )
    LLMFactory.register_model(dummy_model)
    
    # Force discovery failure by using invalid URL
    monkeypatch.setenv('AUTOBYTEUS_LLM_SERVER_URL', 'http://invalid-server:9999')
    
    await AutobyteusModelProvider.discover_and_register()
    
    # Verify dummy model remains
    assert len(LLMFactory.get_models_for_provider(LLMProvider.AUTOBYTEUS)) == 1
    assert LLMFactory.get_models_for_provider(LLMProvider.AUTOBYTEUS)[0].value == "backup-model"
