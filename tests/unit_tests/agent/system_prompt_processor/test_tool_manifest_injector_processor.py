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
    def _factory(use_xml: bool, provider: LLMProvider):
        mock_model = MagicMock(spec=LLMModel)
        mock_model.provider = provider
        mock_llm_instance = MagicMock(spec=BaseLLM)
        mock_llm_instance.model = mock_model
        mock_config = MagicMock(spec=AgentConfig)
        mock_config.use_xml_tool_format = use_xml
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

def test_process_prompt_without_placeholder(processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests that the prompt is unchanged if the placeholder is missing."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "This is a simple prompt without variables."
    processed_prompt = processor.process(original_prompt, {"SomeTool": MagicMock(spec=BaseTool)}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt

def test_process_with_no_tools(processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that a 'no tools' message is injected when no tools are provided."""
    caplog.set_level(logging.INFO)
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    prompt_with_placeholder = "Tools: {{tools}}"
    processed_prompt = processor.process(prompt_with_placeholder, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated" in caplog.text
    assert "No tools available for this agent." in processed_prompt
    assert "{{tools}}" not in processed_prompt

def test_process_only_placeholder_prepends_default_prefix(processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests that the default prefix is added when the prompt only contains the placeholder."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    # Test with different amounts of whitespace to confirm robustness
    for prompt_only_placeholder in ["{{tools}}", "  {{ tools }}  ", "\n{{tools}}\n"]:
        processed_prompt = processor.process(prompt_only_placeholder, {}, mock_context.agent_id, mock_context)
        
        assert processed_prompt.startswith(ToolManifestInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT)
        assert "No tools available for this agent." in processed_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.ToolManifestProvider')
def test_process_with_mocked_manifest(MockToolManifestProvider, processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests successful injection of a tool manifest from the provider."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    mock_provider_instance = MockToolManifestProvider.return_value
    mock_provider_instance.provide.return_value = "---MOCK TOOL MANIFEST---"

    tools = {"AlphaTool": MagicMock(spec=BaseTool)}
    prompt = "Use these tools: {{ tools }}" # Note the spaces
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    # Assert that the provide method was called correctly
    mock_provider_instance.provide.assert_called_once()
    # Assert that the prompt was rendered correctly
    assert processed_prompt == "Use these tools: \n---MOCK TOOL MANIFEST---"
    assert "{{tools}}" not in processed_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.ToolManifestProvider')
def test_process_when_manifest_provider_fails(MockToolManifestProvider, processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that the processor injects an error message if the manifest provider fails."""
    caplog.set_level(logging.ERROR)
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    mock_provider_instance = MockToolManifestProvider.return_value
    mock_provider_instance.provide.side_effect = RuntimeError("Manifest Generation Failed")

    tools = {"AlphaTool": MagicMock(spec=BaseTool)}
    prompt = "Tools list: {{tools}}"
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    # Assert that the error was logged
    assert "An unexpected error occurred during tool manifest generation" in caplog.text
    # Assert that the fallback error message was injected
    assert "Error: Could not generate tool descriptions." in processed_prompt
    assert "{{tools}}" not in processed_prompt

def test_process_with_invalid_jinja_template(processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that an invalid Jinja2 template is returned as-is."""
    caplog.set_level(logging.ERROR)
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    # This prompt has an unclosed Jinja2 expression
    invalid_prompt = "This is an invalid template {{ tools "
    
    processed_prompt = processor.process(invalid_prompt, {"SomeTool": MagicMock(spec=BaseTool)}, mock_context.agent_id, mock_context)

    # Assert error was logged
    assert "Failed to create PromptTemplate from system prompt" in caplog.text
    # Assert the original, unmodified prompt is returned
    assert processed_prompt == invalid_prompt
