"""
JsonInitializationState: Analyzes potential JSON tool calls after a '{' or '[' is detected.

This state buffers characters to determine if a JSON structure is a tool call
based on a signature check strategy. Used for providers like OpenAI that use
JSON format instead of XML.
"""
from typing import TYPE_CHECKING, Optional, List

from .base_state import BaseState

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class JsonToolSignatureChecker:
    """
    Checks if a JSON buffer matches known tool call signatures.
    
    Common JSON tool call formats:
    - OpenAI: {"name": "tool_name", "arguments": {...}}
    - Anthropic: Similar structure
    
    Returns:
    - 'match': Buffer matches a tool signature
    - 'partial': Buffer could still match (keep buffering)
    - 'no_match': Buffer definitely not a tool call
    """
    
    def __init__(self, patterns: Optional[List[str]] = None):
        """
        Initialize with custom patterns or defaults.
        
        Args:
            patterns: List of JSON prefixes that indicate tool calls.
                     Uses defaults if not provided.
        """
        from ..parser_context import ParserConfig
        self._patterns = patterns or ParserConfig.DEFAULT_JSON_PATTERNS
    
    def check_signature(self, buffer: str) -> str:
        """
        Check if the buffer matches a tool call signature.
        
        Returns 'match', 'partial', or 'no_match'.
        """
        # Normalize whitespace for checking
        normalized = buffer.replace(" ", "").replace("\n", "").replace("\t", "")
        
        for pattern in self._patterns:
            normalized_pattern = pattern.replace(" ", "")
            
            # Exact prefix match - it's a tool call
            if normalized.startswith(normalized_pattern):
                return 'match'
            
            # Could still become this pattern
            if normalized_pattern.startswith(normalized):
                return 'partial'
        
        # Check if we're still in the opening portion
        # Allow for whitespace variations like { "name" or {\n"name"
        if len(normalized) < 8:  # Short buffer, still checking
            if normalized in ['', '{', '[', '{"', '[{', '{"n', '{"na', '{"nam']:
                return 'partial'
        
        return 'no_match'


class JsonInitializationState(BaseState):
    """
    Analyzes a potential JSON tool call to determine if it's a known format.
    
    This state is entered when a '{' or '[' is detected and JSON parsing is enabled.
    It buffers characters to check for tool call signatures.
    """
    
    def __init__(self, context: "ParserContext"):
        super().__init__(context)
        # Consume the trigger character that caused this transition
        trigger = self.context.peek_char()
        self.context.advance()
        self._signature_buffer = trigger if trigger else ""
        # Use patterns from config
        self._checker = JsonToolSignatureChecker(context.json_tool_patterns)

    def run(self) -> None:
        """
        Buffer characters and check for tool call signatures.
        
        If a match is found, transitions to ToolParsingState (JSON mode).
        If no match, reverts the buffer to text.
        """
        from .text_state import TextState
        from .json_tool_parsing_state import JsonToolParsingState
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._signature_buffer += char
            self.context.advance()
            
            match = self._checker.check_signature(self._signature_buffer)
            
            if match == 'match':
                # Found a tool signature
                if self.context.parse_tool_calls:
                    # Rewind so JsonToolParsingState can consume from start
                    self.context.rewind_by(len(self._signature_buffer))
                    self.context.transition_to(
                        JsonToolParsingState(self.context, self._signature_buffer)
                    )
                else:
                    # Tool parsing disabled - emit as text
                    self.context.append_text_segment(self._signature_buffer)
                    self.context.transition_to(TextState(self.context))
                return
            
            if match == 'no_match':
                # Not a tool call - emit as text
                self.context.append_text_segment(self._signature_buffer)
                self.context.transition_to(TextState(self.context))
                return
            
            # 'partial' - continue buffering

    def finalize(self) -> None:
        """
        Called when stream ends while checking JSON signature.
        
        Emit buffered content as text.
        """
        from .text_state import TextState
        
        if self._signature_buffer:
            self.context.append_text_segment(self._signature_buffer)
            self._signature_buffer = ""
        
        self.context.transition_to(TextState(self.context))
