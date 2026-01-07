"""
XmlToolParsingStateRegistry: Central registry for mapping tool names to their parsing states.

This singleton allows:
1.  Core defaults (write_file, patch_file, run_bash) to be registered.
2.  External consumers (users, plugins) to register custom states for new tools (e.g., patch_prompt).
3.  The main XmlTagInitializationState to perform dynamic lookups instead of hardcoded if/else.
"""
from typing import Dict, Optional, Type, TYPE_CHECKING
from autobyteus.utils.singleton import SingletonMeta

if TYPE_CHECKING:
    from .states.base_state import BaseState

class XmlToolParsingStateRegistry(metaclass=SingletonMeta):
    """
    Registry for dispatching <tool name="..."> tags to specific Parser State classes.
    """

    def __init__(self):
        # Maps tool_name -> State Class
        self._tool_states: Dict[str, Type["BaseState"]] = {}
        
        # Register Core Defaults
        # We perform local imports to avoid top-level circular dependencies
        from .states.xml_write_file_tool_parsing_state import XmlWriteFileToolParsingState
        from .states.xml_patch_file_tool_parsing_state import XmlPatchFileToolParsingState
        from .states.xml_run_bash_tool_parsing_state import XmlRunBashToolParsingState
        from .tool_constants import TOOL_NAME_WRITE_FILE, TOOL_NAME_PATCH_FILE, TOOL_NAME_RUN_BASH
        
        self.register_tool_state(TOOL_NAME_WRITE_FILE, XmlWriteFileToolParsingState)
        self.register_tool_state(TOOL_NAME_PATCH_FILE, XmlPatchFileToolParsingState)
        self.register_tool_state(TOOL_NAME_RUN_BASH, XmlRunBashToolParsingState)

    def register_tool_state(self, tool_name: str, state_class: Type["BaseState"]) -> None:
        """
        Register a custom parsing state for a specific tool.

        Args:
            tool_name: The name of the tool (e.g., 'write_file', 'patch_prompt').
            state_class: The class handling the parsing (must inherit from BaseState).
        """
        self._tool_states[tool_name] = state_class

    def get_state_for_tool(self, tool_name: str) -> Optional[Type["BaseState"]]:
        """
        Retrieve the parsing state class for a given tool.

        Args:
            tool_name: The tool name found in the XML tag.

        Returns:
            The registered state class, or None if not found.
        """
        return self._tool_states.get(tool_name)
