"""
StateFactory: Factory for creating parser states.

This pattern helps avoid circular imports between states by providing
a central location for state instantiation.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser_context import ParserContext
    from .states.base_state import BaseState


class StateFactory:
    """
    Factory for creating parser state instances.
    
    This avoids circular imports between state classes by providing
    lazy imports at the point of creation.
    """
    
    @staticmethod
    def text_state(context: "ParserContext") -> "BaseState":
        """Create a TextState instance."""
        from .states.text_state import TextState
        return TextState(context)
    
    @staticmethod
    def xml_tag_init_state(context: "ParserContext") -> "BaseState":
        """Create an XmlTagInitializationState instance."""
        from .states.xml_tag_initialization_state import XmlTagInitializationState
        return XmlTagInitializationState(context)
    
    @staticmethod
    def file_parsing_state(context: "ParserContext", opening_tag: str) -> "BaseState":
        """Create a FileParsingState instance."""
        from .states.file_parsing_state import FileParsingState
        return FileParsingState(context, opening_tag)
    
    @staticmethod
    def bash_parsing_state(context: "ParserContext", opening_tag: str) -> "BaseState":
        """Create a BashParsingState instance."""
        from .states.bash_parsing_state import BashParsingState
        return BashParsingState(context, opening_tag)
    
    @staticmethod
    def tool_parsing_state(context: "ParserContext", signature_buffer: str) -> "BaseState":
        """Create a ToolParsingState instance."""
        from .states.tool_parsing_state import ToolParsingState
        return ToolParsingState(context, signature_buffer)
    
    @staticmethod
    def iframe_parsing_state(context: "ParserContext", initial_content: str) -> "BaseState":
        """Create an IframeParsingState instance."""
        from .states.iframe_parsing_state import IframeParsingState
        return IframeParsingState(context, initial_content)
    
    @staticmethod
    def json_init_state(context: "ParserContext") -> "BaseState":
        """Create a JsonInitializationState instance."""
        from .states.json_initialization_state import JsonInitializationState
        return JsonInitializationState(context)
    
    @staticmethod
    def json_tool_parsing_state(context: "ParserContext", signature_buffer: str) -> "BaseState":
        """Create a JsonToolParsingState instance."""
        from .states.json_tool_parsing_state import JsonToolParsingState
        return JsonToolParsingState(context, signature_buffer)
