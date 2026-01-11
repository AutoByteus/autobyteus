# file: autobyteus/tests/unit_tests/agent/system_prompt_processor/test_tool_manifest_injector_processor.py
import pytest
import logging
from unittest.mock import MagicMock, patch

from autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor import ToolManifestInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider


@pytest.fixture
def mock_context_factory():
    """A factory fixture to create a mock AgentContext for testing."""
    def _factory(provider: LLMProvider):
        mock_model = MagicMock(spec=LLMModel)
        mock_model.provider = provider
        mock_llm_instance = MagicMock(spec=BaseLLM)
        mock_llm_instance.model = mock_model
        mock_config = MagicMock(spec=AgentConfig)
        context = MagicMock(spec=AgentContext)
        context.agent_id = "test_agent_123"
        context.config = mock_config
        context.llm_instance = mock_llm_instance
        return context
    return _factory


@pytest.fixture
def processor() -> ToolManifestInjectorProcessor:
    """Provides an instance of the processor for tests."""
    return ToolManifestInjectorProcessor()


def test_get_name(processor: ToolManifestInjectorProcessor):
    """Tests that the processor returns the correct name."""
    assert processor.get_name() == "ToolManifestInjector"


def test_is_mandatory(processor: ToolManifestInjectorProcessor):
    """Tests that the processor is mandatory."""
    assert processor.is_mandatory() is True


def test_process_with_no_tools(processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that the prompt is unchanged when no tools are provided."""
    caplog.set_level(logging.INFO)
    mock_context = mock_context_factory(provider=LLMProvider.OPENAI)
    original_prompt = "You are a helpful assistant."
    
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert "No tools configured" in caplog.text
    assert processed_prompt == original_prompt


@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.ToolManifestProvider')
@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_appends_tools_section(mock_registry, MockToolManifestProvider, processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests that tools are appended as an 'Accessible Tools' section."""
    mock_context = mock_context_factory(provider=LLMProvider.ANTHROPIC)
    
    # Mock the tool definition lookup
    mock_tool_def = MagicMock()
    mock_registry.get_tool_definition.return_value = mock_tool_def
    
    # Mock the manifest provider
    mock_provider_instance = MockToolManifestProvider.return_value
    mock_provider_instance.provide.return_value = "---MOCK TOOL MANIFEST---"

    tools = {"AlphaTool": MagicMock(spec=BaseTool)}
    original_prompt = "You are a helpful assistant."
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    # Assert the manifest provider was called
    mock_provider_instance.provide.assert_called_once()
    
    # Assert the prompt was appended correctly
    assert processed_prompt.startswith(original_prompt)
    assert "## Accessible Tools" in processed_prompt
    assert "---MOCK TOOL MANIFEST---" in processed_prompt


@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_with_no_tool_definitions(mock_registry, processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that the prompt is unchanged when tool definitions are not found."""
    caplog.set_level(logging.WARNING)
    mock_context = mock_context_factory(provider=LLMProvider.OPENAI)
    
    # Mock no tool definitions found
    mock_registry.get_tool_definition.return_value = None

    tools = {"UnknownTool": MagicMock(spec=BaseTool)}
    original_prompt = "You are a helpful assistant."
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    assert "no definitions found in registry" in caplog.text
    assert processed_prompt == original_prompt


@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.ToolManifestProvider')
@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_when_manifest_provider_fails(mock_registry, MockToolManifestProvider, processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that the original prompt is returned if the manifest provider fails."""
    caplog.set_level(logging.ERROR)
    mock_context = mock_context_factory(provider=LLMProvider.ANTHROPIC)
    
    # Mock the tool definition lookup
    mock_tool_def = MagicMock()
    mock_registry.get_tool_definition.return_value = mock_tool_def
    
    # Mock the provider to raise an exception
    mock_provider_instance = MockToolManifestProvider.return_value
    mock_provider_instance.provide.side_effect = RuntimeError("Manifest Generation Failed")

    tools = {"AlphaTool": MagicMock(spec=BaseTool)}
    original_prompt = "You are a helpful assistant."
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    # Assert that the error was logged
    assert "Failed to generate tool manifest" in caplog.text
    # Assert original prompt is returned on failure
    assert processed_prompt == original_prompt


@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.ToolManifestProvider')
@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_logs_tool_count(mock_registry, MockToolManifestProvider, processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that the processor logs the number of injected tools."""
    caplog.set_level(logging.INFO)
    mock_context = mock_context_factory(provider=LLMProvider.OPENAI)
    
    # Mock the tool definition lookup
    mock_tool_def = MagicMock()
    mock_registry.get_tool_definition.return_value = mock_tool_def
    
    # Mock the manifest provider
    mock_provider_instance = MockToolManifestProvider.return_value
    mock_provider_instance.provide.return_value = "Tool manifest here"

    tools = {
        "ToolA": MagicMock(spec=BaseTool),
        "ToolB": MagicMock(spec=BaseTool),
    }
    
    processor.process("Base prompt", tools, mock_context.agent_id, mock_context)

    assert "Injected 2 tools" in caplog.text
