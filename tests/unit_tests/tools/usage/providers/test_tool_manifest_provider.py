# file: autobyteus/tests/unit_tests/tools/usage/test_tool_manifest_provider.py
import pytest
import logging
import json
from unittest.mock import MagicMock

from autobyteus.tools.usage.providers.tool_manifest_provider import ToolManifestProvider
from autobyteus.tools.registry import ToolDefinition
from autobyteus.llm.providers import LLMProvider

# Helper to create mock definitions for testing
def create_mock_tool_definition(name: str, xml_schema: str, xml_example: str, json_schema: dict, json_example: dict):
    """Creates a mock ToolDefinition for testing purposes."""
    mock_def = MagicMock(spec=ToolDefinition)
    mock_def.name = name
    mock_def.get_usage_xml.return_value = xml_schema
    mock_def.get_usage_xml_example.return_value = xml_example
    mock_def.get_usage_json.return_value = json_schema
    mock_def.get_usage_json_example.return_value = json_example
    return mock_def

@pytest.fixture
def provider() -> ToolManifestProvider:
    """Provides an instance of the ToolManifestProvider."""
    return ToolManifestProvider()

@pytest.fixture
def mock_tool_def_alpha() -> ToolDefinition:
    """Provides a mock ToolDefinition for a tool named 'Alpha'."""
    schema_xml = "<tool name='Alpha' />"
    example_xml = "<tool name='Alpha'><arguments/></tool>"
    schema_json = {"name": "Alpha", "description": "Tool Alpha"}
    example_json = {"name": "Alpha", "arguments": {}}
    return create_mock_tool_definition("Alpha", schema_xml, example_xml, schema_json, example_json)

@pytest.fixture
def mock_tool_def_beta() -> ToolDefinition:
    """Provides a mock ToolDefinition for a tool named 'Beta'."""
    schema_xml = "<tool name='Beta' />"
    example_xml = "<tool name='Beta'><arguments/></tool>"
    schema_json = {"name": "Beta", "description": "Tool Beta"}
    example_json = {"name": "Beta", "arguments": {"p": "v"}}
    return create_mock_tool_definition("Beta", schema_xml, example_xml, schema_json, example_json)


def test_provide_single_tool_xml(provider: ToolManifestProvider, mock_tool_def_alpha: ToolDefinition):
    """Tests generating a manifest for a single tool in XML format."""
    # --- ARRANGE ---
    # Get the expected values from the mock *before* calling the function under test.
    expected_schema = mock_tool_def_alpha.get_usage_xml()
    expected_example = mock_tool_def_alpha.get_usage_xml_example()
    # Reset mocks after getting values, so we can assert call counts accurately from the 'Act' phase.
    mock_tool_def_alpha.get_usage_xml.reset_mock()
    mock_tool_def_alpha.get_usage_xml_example.reset_mock()

    expected_block = (
        f"{provider.SCHEMA_HEADER}\n{expected_schema}\n\n"
        f"{provider.EXAMPLE_HEADER}\n{expected_example}"
    )

    # --- ACT ---
    manifest = provider.provide([mock_tool_def_alpha], use_xml=True, provider=LLMProvider.ANTHROPIC)

    # --- ASSERT ---
    assert manifest == expected_block
    mock_tool_def_alpha.get_usage_xml.assert_called_once_with(provider=LLMProvider.ANTHROPIC)
    mock_tool_def_alpha.get_usage_xml_example.assert_called_once_with(provider=LLMProvider.ANTHROPIC)

def test_provide_single_tool_json(provider: ToolManifestProvider, mock_tool_def_alpha: ToolDefinition):
    """Tests generating a manifest for a single tool in JSON format."""
    # --- ARRANGE ---
    expected_schema = mock_tool_def_alpha.get_usage_json()
    expected_example = mock_tool_def_alpha.get_usage_json_example()
    mock_tool_def_alpha.get_usage_json.reset_mock()
    mock_tool_def_alpha.get_usage_json_example.reset_mock()
    
    # --- ACT ---
    manifest = provider.provide([mock_tool_def_alpha], use_xml=False, provider=LLMProvider.OPENAI)
    
    # --- ASSERT ---
    parsed_json = json.loads(manifest)
    assert isinstance(parsed_json, list)
    assert len(parsed_json) == 1
    
    manifest_obj = parsed_json[0]
    assert manifest_obj["tool_definition"] == expected_schema
    assert manifest_obj["example_call"] == expected_example
    mock_tool_def_alpha.get_usage_json.assert_called_once_with(provider=LLMProvider.OPENAI)
    mock_tool_def_alpha.get_usage_json_example.assert_called_once_with(provider=LLMProvider.OPENAI)

def test_provide_multiple_tools_xml(provider: ToolManifestProvider, mock_tool_def_alpha: ToolDefinition, mock_tool_def_beta: ToolDefinition):
    """Tests that manifests for multiple tools are joined correctly in XML."""
    # --- ARRANGE ---
    alpha_schema = mock_tool_def_alpha.get_usage_xml()
    alpha_example = mock_tool_def_alpha.get_usage_xml_example()
    beta_schema = mock_tool_def_beta.get_usage_xml()
    beta_example = mock_tool_def_beta.get_usage_xml_example()

    alpha_block = f"{provider.SCHEMA_HEADER}\n{alpha_schema}\n\n{provider.EXAMPLE_HEADER}\n{alpha_example}"
    beta_block = f"{provider.SCHEMA_HEADER}\n{beta_schema}\n\n{provider.EXAMPLE_HEADER}\n{beta_example}"

    # --- ACT ---
    manifest = provider.provide([mock_tool_def_alpha, mock_tool_def_beta], use_xml=True)
    
    # --- ASSERT ---
    assert alpha_block in manifest
    assert beta_block in manifest
    assert manifest == f"{alpha_block}\n\n{beta_block}"

def test_provide_with_empty_tool_list(provider: ToolManifestProvider):
    """Tests that an empty string is returned for an empty list of tools."""
    xml_manifest = provider.provide([], use_xml=True)
    assert xml_manifest == ""
    
    json_manifest = provider.provide([], use_xml=False)
    # For JSON, it should be an empty list string
    assert json_manifest == "[\n\n]"

def test_provide_skips_tool_on_generation_error(provider: ToolManifestProvider, mock_tool_def_alpha: ToolDefinition, mock_tool_def_beta: ToolDefinition, caplog):
    """Tests that if one tool fails, the others are still included in the manifest."""
    caplog.set_level(logging.ERROR)
    
    # --- ARRANGE ---
    mock_tool_def_alpha.get_usage_xml.side_effect = ValueError("XML Generation Failed")
    beta_schema = mock_tool_def_beta.get_usage_xml()
    beta_example = mock_tool_def_beta.get_usage_xml_example()
    
    # --- ACT ---
    manifest = provider.provide([mock_tool_def_alpha, mock_tool_def_beta], use_xml=True)

    # --- ASSERT ---
    assert "Failed to generate manifest block for tool 'Alpha'" in caplog.text
    assert "XML Generation Failed" in caplog.text

    expected_beta_block = f"{provider.SCHEMA_HEADER}\n{beta_schema}\n\n{provider.EXAMPLE_HEADER}\n{beta_example}"
    assert manifest == expected_beta_block
    
    assert "Alpha" not in manifest
