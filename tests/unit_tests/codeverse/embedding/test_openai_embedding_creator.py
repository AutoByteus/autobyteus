import pytest
import numpy as np
from unittest.mock import patch, Mock

from autobyteus.embeding.openai_embedding_creator import OpenAIEmbeddingCreator


@pytest.fixture
def mock_openai_api():
    with patch('autobyteus.semantic_code.embedding.openai_embedding_creator.openai', autospec=True) as mock_openai:
        yield mock_openai

@pytest.fixture
def mock_logger():
    with patch('autobyteus.semantic_code.embedding.openai_embedding_creator.logger', autospec=True) as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_config():
    with patch('autobyteus.semantic_code.embedding.openai_embedding_creator.config', autospec=True) as mock_config:
        mock_config.get.side_effect = lambda key, default=None: 'dummy_value'
        yield mock_config

def test_initialization_reads_config_values(mock_config):
    creator = OpenAIEmbeddingCreator()
    assert creator.api_key == 'dummy_value', 'API key not read from config'
    assert creator.model_name == 'dummy_value', 'Model name not read from config'

def test_create_embedding_calls_api_with_correct_parameters(mock_openai_api, mock_config):
    creator = OpenAIEmbeddingCreator()
    creator.create_embedding("test_text")
    mock_openai_api.Embedding.create.assert_called_once_with(input="test_text", model='dummy_value')

@pytest.mark.parametrize("input_text", ["", None])
def test_create_embedding_with_invalid_input_returns_none(input_text, mock_openai_api, mock_config):
    creator = OpenAIEmbeddingCreator()
    assert creator.create_embedding(input_text) is None, f'Embedding should not be created for input {input_text}'

def test_create_embedding_on_api_exception_returns_none(mock_openai_api, mock_config, mock_logger):
    mock_openai_api.Embedding.create.side_effect = Exception('API Error')
    creator = OpenAIEmbeddingCreator()
    assert creator.create_embedding("test_text") is None, 'Embedding should not be created on API exception'

def test_create_embedding_successful_execution_returns_embedding(mock_openai_api, mock_config):
    embedding_response = {"data": [{"embedding": [1, 2, 3]}]}
    mock_openai_api.Embedding.create.return_value = embedding_response
    creator = OpenAIEmbeddingCreator()
    expected_embedding = np.array([1, 2, 3], dtype=np.float32).tobytes()
    assert creator.create_embedding("test_text") == expected_embedding, 'Embedding not created successfully'
