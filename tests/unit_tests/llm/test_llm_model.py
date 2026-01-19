# file: autobyteus/tests/unit_tests/llm/test_llm_model.py
"""
Unit tests for LLMModel config_schema functionality.
"""
import pytest
from unittest.mock import MagicMock

from autobyteus.llm.models import LLMModel, ModelInfo
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType


class TestLLMModelConfigSchema:
    """Tests for config_schema field on LLMModel."""
    
    def test_llm_model_without_config_schema(self):
        """LLMModel should work without config_schema (backward compatible)."""
        mock_llm_class = MagicMock()
        
        model = LLMModel(
            name="test-model",
            value="test-model-v1",
            provider=LLMProvider.OPENAI,
            llm_class=mock_llm_class,
            canonical_name="test-model",
        )
        
        assert model.config_schema is None
        assert model.name == "test-model"
    
    def test_llm_model_with_config_schema(self):
        """LLMModel should accept and store config_schema."""
        mock_llm_class = MagicMock()
        schema = ParameterSchema(parameters=[
            ParameterDefinition(
                name="thinking_level",
                param_type=ParameterType.ENUM,
                description="Thinking level for reasoning",
                enum_values=["minimal", "low", "medium", "high"],
                default_value="medium"
            )
        ])
        
        model = LLMModel(
            name="test-model",
            value="test-model-v1",
            provider=LLMProvider.OPENAI,
            llm_class=mock_llm_class,
            canonical_name="test-model",
            config_schema=schema
        )
        
        assert model.config_schema is not None
        assert len(model.config_schema.parameters) == 1
        assert model.config_schema.parameters[0].name == "thinking_level"
    
    def test_to_model_info_without_config_schema(self):
        """to_model_info should return None for config_schema when not set."""
        mock_llm_class = MagicMock()
        
        model = LLMModel(
            name="test-model",
            value="test-model-v1",
            provider=LLMProvider.OPENAI,
            llm_class=mock_llm_class,
            canonical_name="test-model",
        )
        
        model_info = model.to_model_info()
        
        assert isinstance(model_info, ModelInfo)
        assert model_info.config_schema is None
    
    def test_to_model_info_with_config_schema(self):
        """to_model_info should serialize config_schema to dict."""
        mock_llm_class = MagicMock()
        schema = ParameterSchema(parameters=[
            ParameterDefinition(
                name="budget_tokens",
                param_type=ParameterType.INTEGER,
                description="Token budget for thinking",
                min_value=1024,
                max_value=64000,
                default_value=10000
            )
        ])
        
        model = LLMModel(
            name="claude-test",
            value="claude-test-v1",
            provider=LLMProvider.ANTHROPIC,
            llm_class=mock_llm_class,
            canonical_name="claude-test",
            config_schema=schema
        )
        
        model_info = model.to_model_info()
        
        assert isinstance(model_info, ModelInfo)
        assert model_info.config_schema is not None
        assert isinstance(model_info.config_schema, dict)
        assert "parameters" in model_info.config_schema
        assert len(model_info.config_schema["parameters"]) == 1
        
        param = model_info.config_schema["parameters"][0]
        assert param["name"] == "budget_tokens"
        assert param["type"] == "integer"
        assert param["min_value"] == 1024
        assert param["max_value"] == 64000

    def test_to_model_info_preserves_all_fields(self):
        """to_model_info should correctly map all LLMModel fields."""
        mock_llm_class = MagicMock()
        
        model = LLMModel(
            name="test-model",
            value="test-model-v1",
            provider=LLMProvider.GEMINI,
            llm_class=mock_llm_class,
            canonical_name="test-canonical",
            runtime=LLMRuntime.API,
            host_url=None
        )
        
        model_info = model.to_model_info()
        
        assert model_info.model_identifier == "test-model"  # API runtime uses name
        assert model_info.display_name == "test-model"
        assert model_info.value == "test-model-v1"
        assert model_info.canonical_name == "test-canonical"
        assert model_info.provider == "GEMINI"
        assert model_info.runtime == "api"
        assert model_info.host_url is None
