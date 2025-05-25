# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_description_injector_processor.py
import logging
from typing import Dict, List, TYPE_CHECKING

from .base_processor import BaseSystemPromptProcessor # Relative import

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolDescriptionInjectorProcessor(BaseSystemPromptProcessor):
    """
    A system prompt processor that injects tool descriptions into the prompt.
    It looks for a specific placeholder (default: "{{tools}}") in the system prompt
    and replaces it with XML descriptions of the available tools.
    If the system prompt consists *only* of the placeholder, a default
    instructional prefix is added.
    """
    PLACEHOLDER = "{{tools}}"
    DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT = (
        "You are a helpful assistant. You have access to the following tools. "
        "Please use them as appropriate based on the user's request and the tool descriptions provided below:\n\n"
    )

    @classmethod
    def get_name(cls) -> str:
        """Returns the unique registration name for this processor."""
        return "ToolDescriptionInjector"

    def process(self,
                system_prompt: str,
                tool_instances: Dict[str, 'BaseTool'],
                agent_id: str) -> str:
        """
        Processes the system prompt to inject tool descriptions.

        Args:
            system_prompt: The current system prompt string.
            tool_instances: A dictionary of instantiated tools.
            agent_id: The ID of the agent (for logging).

        Returns:
            The processed system prompt string with tool descriptions injected.
        """
        if self.PLACEHOLDER not in system_prompt:
            logger.debug(f"ToolDescriptionInjectorProcessor: Placeholder '{self.PLACEHOLDER}' not found in system prompt for agent '{agent_id}'. Prompt unchanged.")
            return system_prompt

        tool_usage_xml_parts: List[str] = []
        actual_tools_description: str # This will hold the pure XML content

        if not tool_instances:
            logger.warning(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' contains '{self.PLACEHOLDER}', "
                           "but no tools are instantiated. Replacing with 'No tools available.'")
            actual_tools_description = "No tools available for this agent."
        else:
            for tool_name, tool_instance in tool_instances.items():
                try:
                    usage_xml = tool_instance.tool_usage_xml() 
                    if usage_xml: 
                        tool_usage_xml_parts.append(usage_xml)
                    else:
                        logger.warning(f"ToolDescriptionInjectorProcessor: Tool '{tool_name}' for agent '{agent_id}' returned empty usage XML.")
                        tool_usage_xml_parts.append(f"<tool_error name=\"{tool_name}\">Error: Usage information is empty for this tool.</tool_error>")
                except Exception as e:
                    logger.error(f"ToolDescriptionInjectorProcessor: Failed to get usage XML for tool '{tool_name}' for agent '{agent_id}': {e}", exc_info=True)
                    tool_usage_xml_parts.append(f"<tool_error name=\"{tool_name}\">Error: Usage information could not be generated for this tool.</tool_error>")
            
            if tool_usage_xml_parts:
                actual_tools_description = "\n".join(tool_usage_xml_parts) # Pure XML, no leading/trailing newlines from here
            else:
                logger.warning(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' has '{self.PLACEHOLDER}', "
                               "but failed to generate or retrieve usage for any tool. Replacing with 'Tool usage information is currently unavailable.'")
                actual_tools_description = "Tool usage information is currently unavailable."
        
        # Check if the original prompt was *only* the placeholder
        if system_prompt.strip() == self.PLACEHOLDER:
            logger.info(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' was only '{self.PLACEHOLDER}'. "
                        f"Prepending default instructions.")
            # Prepend default instructions and then the tool descriptions.
            # The actual_tools_description doesn't have an extra leading newline from its generation.
            # The DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT ends with \n\n, so this should format well.
            final_system_prompt = self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + actual_tools_description
        else:
            # The user provided surrounding text, so just replace the placeholder.
            # We add a leading newline to actual_tools_description for better separation if the placeholder
            # is on its own line surrounded by other text.
            formatted_tools_block_for_replacement = "\n" + actual_tools_description
            final_system_prompt = system_prompt.replace(self.PLACEHOLDER, formatted_tools_block_for_replacement)
        
        logger.info(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' processed. Placeholder '{self.PLACEHOLDER}' was handled.")
        return final_system_prompt
