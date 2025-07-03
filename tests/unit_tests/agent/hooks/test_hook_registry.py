# file: autobyteus/tests/unit_tests/agent/hooks/test_hook_registry.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent.hooks import BasePhaseHook, default_phase_hook_registry
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent.context import AgentContext

# These classes will be automatically registered by the PhaseHookMeta metaclass
# when pytest imports this file. This is the core behavior we want to test.

class HookForTestingOne(BasePhaseHook):
    """A concrete hook for testing purposes with a custom name."""
    @classmethod
    def get_name(cls) -> str:
        return "TestHookOne"

    @property
    def source_phase(self) -> AgentOperationalPhase:
        return AgentOperationalPhase.BOOTSTRAPPING

    @property
    def target_phase(self) -> AgentOperationalPhase:
        return AgentOperationalPhase.IDLE

    async def execute(self, context: 'AgentContext') -> None:
        pass # pragma: no cover

class HookForTestingTwo(BasePhaseHook):
    """Another concrete hook for testing, using the default name."""
    # It will be registered under the name "HookForTestingTwo"
    @property
    def source_phase(self) -> AgentOperationalPhase:
        return AgentOperationalPhase.IDLE

    @property
    def target_phase(self) -> AgentOperationalPhase:
        return AgentOperationalPhase.PROCESSING_USER_INPUT

    async def execute(self, context: 'AgentContext') -> None:
        pass # pragma: no cover

def test_hooks_are_auto_registered():
    """
    Tests that the test hooks defined in this file are automatically
    registered in the default_phase_hook_registry upon module import.
    """
    assert "TestHookOne" in default_phase_hook_registry
    assert "HookForTestingTwo" in default_phase_hook_registry
    # Use >= in case other tests or modules also define and register hooks.
    assert len(default_phase_hook_registry) >= 2

def test_get_hook_definition():
    """
    Tests retrieving a hook definition from the registry.
    """
    definition = default_phase_hook_registry.get_hook_definition("TestHookOne")
    assert definition is not None
    assert definition.name == "TestHookOne"
    assert definition.hook_class == HookForTestingOne

    # Test getting a non-existent hook
    non_existent = default_phase_hook_registry.get_hook_definition("NonExistentHook")
    assert non_existent is None

def test_get_hook_instantiates_correctly():
    """
    Tests that the registry can correctly instantiate a hook from its definition.
    """
    hook_instance = default_phase_hook_registry.get_hook("TestHookOne")
    assert hook_instance is not None
    assert isinstance(hook_instance, HookForTestingOne)
    assert isinstance(hook_instance, BasePhaseHook)

    # Check properties on the instance
    assert hook_instance.source_phase == AgentOperationalPhase.BOOTSTRAPPING
    assert hook_instance.target_phase == AgentOperationalPhase.IDLE

    # Test getting a non-existent hook
    non_existent = default_phase_hook_registry.get_hook("NonExistentHook")
    assert non_existent is None

def test_list_hook_names():
    """
    Tests that list_hook_names returns the names of the registered hooks.
    """
    names = default_phase_hook_registry.list_hook_names()
    assert "TestHookOne" in names
    assert "HookForTestingTwo" in names

def test_get_hook_with_non_string_name_returns_none():
    """
    Tests that providing a non-string name returns None as expected.
    """
    assert default_phase_hook_registry.get_hook(123) is None
    assert default_phase_hook_registry.get_hook_definition(None) is None
