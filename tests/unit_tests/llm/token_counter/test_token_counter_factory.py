"""
Unit tests for token_counter_factory to verify graceful handling of unsupported providers.
"""

import pytest
from unittest.mock import MagicMock
from autobyteus.llm.token_counter.token_counter_factory import get_token_counter
from autobyteus.llm.providers import LLMProvider


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    return MagicMock()


def test_get_token_counter_returns_none_for_autobyteus_provider(mock_llm):
    """
    Test that get_token_counter returns None for the AUTOBYTEUS provider
    instead of raising NotImplementedError.
    """
    mock_model = MagicMock()
    mock_model.provider = LLMProvider.AUTOBYTEUS
    mock_model.value = "autobyteus-model"
    
    result = get_token_counter(mock_model, mock_llm)
    
    assert result is None


def test_get_token_counter_returns_none_for_baidu_provider(mock_llm):
    """
    Test that get_token_counter returns None for the BAIDU provider.
    """
    mock_model = MagicMock()
    mock_model.provider = LLMProvider.BAIDU
    mock_model.value = "baidu-model"
    
    result = get_token_counter(mock_model, mock_llm)
    
    assert result is None


def test_get_token_counter_returns_none_for_minimax_provider(mock_llm):
    """
    Test that get_token_counter returns None for the MINIMAX provider.
    """
    mock_model = MagicMock()
    mock_model.provider = LLMProvider.MINIMAX
    mock_model.value = "minimax-model"
    
    result = get_token_counter(mock_model, mock_llm)
    
    assert result is None


def test_get_token_counter_returns_counter_for_openai_provider(mock_llm):
    """
    Test that get_token_counter returns a counter for supported providers.
    """
    mock_model = MagicMock()
    mock_model.provider = LLMProvider.OPENAI
    mock_model.value = "gpt-4o"
    
    result = get_token_counter(mock_model, mock_llm)
    
    assert result is not None
