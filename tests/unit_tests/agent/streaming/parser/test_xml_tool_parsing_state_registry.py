import pytest
from autobyteus.agent.streaming.parser.xml_tool_parsing_state_registry import XmlToolParsingStateRegistry
from autobyteus.agent.streaming.parser.states.base_state import BaseState
from autobyteus.agent.streaming.parser.tool_constants import TOOL_NAME_WRITE_FILE, TOOL_NAME_PATCH_FILE, TOOL_NAME_RUN_BASH

class MockState(BaseState):
    pass

class TestXmlToolParsingStateRegistry:
    def test_registry_singleton(self):
        reg1 = XmlToolParsingStateRegistry()
        reg2 = XmlToolParsingStateRegistry()
        assert reg1 is reg2

    def test_defaults_registered(self):
        registry = XmlToolParsingStateRegistry()
        assert registry.get_state_for_tool(TOOL_NAME_WRITE_FILE) is not None
        assert registry.get_state_for_tool(TOOL_NAME_PATCH_FILE) is not None
        assert registry.get_state_for_tool(TOOL_NAME_RUN_BASH) is not None

    def test_register_custom_state(self):
        registry = XmlToolParsingStateRegistry()
        registry.register_tool_state("custom_tool", MockState)
        assert registry.get_state_for_tool("custom_tool") == MockState

    def test_get_state_case_sensitive(self):
        # Registry keys are case sensitive; normalization happens at usage site
        registry = XmlToolParsingStateRegistry()
        registry.register_tool_state("MyTool", MockState)
        assert registry.get_state_for_tool("MyTool") == MockState
        assert registry.get_state_for_tool("mytool") is None
