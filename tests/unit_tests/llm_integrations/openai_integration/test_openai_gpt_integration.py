import pytest
from autobyteus.llm_integrations.openai_integration.openai_gpt_integration import OpenAIGPTIntegration
from autobyteus.llm_integrations.openai_integration.openai_api_factory import ApiType, OpenAIApiFactory
from autobyteus.llm_integrations.openai_integration.openai_models import OpenAIModel

@pytest.fixture
def mock_openai_api(mocker):
    """Mock the OpenAIApi object."""
    return mocker.Mock(spec=OpenAIApiFactory)

@pytest.fixture
def mock_create_api(mocker, mock_openai_api):
    """Mock the OpenAIApiFactory.create_api method."""
    return mocker.patch("autobyteus.llm_integrations.openai_integration.openai_gpt_integration.OpenAIApiFactory.create_api", return_value=mock_openai_api)

def test_initialization_with_defaults(mock_create_api):
    """Should initialize with default ApiType.CHAT when no parameters are provided."""
    OpenAIGPTIntegration()
    mock_create_api.assert_called_once_with(ApiType.CHAT)

def test_initialization_with_parameters(mock_create_api):
    """Should initialize with provided api_type and model_name."""
    OpenAIGPTIntegration(api_type=ApiType.CHAT, model_name=OpenAIModel.GPT_4)
    mock_create_api.assert_called_once_with(ApiType.CHAT, OpenAIModel.GPT_4)

def test_process_input_messages(mocker):
    """Should correctly process a list of input messages."""
    # Mock the API instance that OpenAIApiFactory.create_api returns
    mock_api_instance = mocker.Mock()
    mock_response = mocker.Mock(content="mock_response")
    mock_api_instance.process_input_messages.return_value = mock_response
    
    # Mock OpenAIApiFactory.create_api to return the mock API instance
    mocker.patch("autobyteus.llm_integrations.openai_integration.openai_gpt_integration.OpenAIApiFactory.create_api", return_value=mock_api_instance)
    
    integration = OpenAIGPTIntegration(api_type=ApiType.CHAT)

    result = integration.process_input_messages(["question_1", "question_2"])

    assert result == "mock_response"
    mock_api_instance.process_input_messages.assert_called_once()

