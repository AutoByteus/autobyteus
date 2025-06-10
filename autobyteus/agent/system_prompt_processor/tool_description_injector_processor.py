# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_description_injector_processor.py
import logging
import json # Added for JSON serialization
from typing import Dict, List, TYPE_CHECKING

from .base_processor import BaseSystemPromptProcessor # Relative import

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class ToolDescriptionInjectorProcessor(BaseSystemPromptProcessor):
    """
    A system prompt processor that injects tool descriptions/schemas into the prompt.
    It looks for a specific placeholder (default: "{{tools}}") in the system prompt
    and replaces it with descriptions of the available tools, formatted as either
    XML or JSON based on the AgentConfig's 'use_xml_tool_format' flag.
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
                agent_id: str,
                context: 'AgentContext'
               ) -> str:
        """
        Processes the system prompt to inject tool descriptions.

        Args:
            system_prompt: The current system prompt string.
            tool_instances: A dictionary of instantiated tools.
            agent_id: The ID of the agent (for logging).
            context: The agent's context, used to access the AgentConfig.

        Returns:
            The processed system prompt string with tool descriptions injected.
        """
        if self.PLACEHOLDER not in system_prompt:
            logger.debug(f"ToolDescriptionInjectorProcessor: Placeholder '{self.PLACEHOLDER}' not found in system prompt for agent '{agent_id}'. Prompt unchanged.")
            return system_prompt

        use_xml_format = context.config.use_xml_tool_format
        chosen_format_str = "XML" if use_xml_format else "JSON"
        logger.debug(f"ToolDescriptionInjectorProcessor for agent '{agent_id}': Using {chosen_format_str} format for tool descriptions.")

        tool_description_parts: List[str] = []
        actual_tools_description: str 

        if not tool_instances:
            logger.warning(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' contains '{self.PLACEHOLDER}', "
                           "but no tools are instantiated. Replacing with 'No tools available.'")
            actual_tools_description = "No tools available for this agent."
        else:
            for tool_name, tool_instance in tool_instances.items():
                try:
                    description_str: str
                    if use_xml_format:
                        description_str = tool_instance.tool_usage_xml() 
                    else:
                        description_dict = tool_instance.tool_usage_json()
                        description_str = json.dumps(description_dict, indent=2)
                    
                    if description_str: 
                        tool_description_parts.append(description_str)
                    else:
                        logger.warning(f"ToolDescriptionInjectorProcessor: Tool '{tool_name}' for agent '{agent_id}' returned empty usage {chosen_format_str} description.")
                        # Provide a format-specific error placeholder if needed
                        if use_xml_format:
                            tool_description_parts.append(f"<tool_error name=\"{tool_name}\">Error: Usage information is empty for this tool.</tool_error>")
                        else:
                            tool_description_parts.append(json.dumps({"tool_error": {"name": tool_name, "message": "Error: Usage information is empty for this tool."}}))
                except Exception as e:
                    logger.error(f"ToolDescriptionInjectorProcessor: Failed to get usage {chosen_format_str} for tool '{tool_name}' for agent '{agent_id}': {e}", exc_info=True)
                    if use_xml_format:
                        tool_description_parts.append(f"<tool_error name=\"{tool_name}\">Error: Usage information could not be generated for this tool.</tool_error>")
                    else:
                        tool_description_parts.append(json.dumps({"tool_error": {"name": tool_name, "message": "Error: Usage information could not be generated for this tool."}}))

            if tool_description_parts:
                actual_tools_description = "\n".join(tool_description_parts) 
            else:
                logger.warning(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' has '{self.PLACEHOLDER}', "
                               f"but failed to generate or retrieve usage for any tool in {chosen_format_str} format. Replacing with 'Tool usage information is currently unavailable.'")
                actual_tools_description = "Tool usage information is currently unavailable."
        
        # Use strip() to handle cases like "  {{tools}}  "
        if system_prompt.strip() == self.PLACEHOLDER:
            logger.info(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' was only '{self.PLACEHOLDER}'. "
                        f"Prepending default instructions.")
            final_system_prompt = self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + actual_tools_description
        else:
            formatted_tools_block_for_replacement = "\n" + actual_tools_description
            final_system_prompt = system_prompt.replace(self.PLACEHOLDER, formatted_tools_block_for_replacement)
        
        logger.info(f"ToolDescriptionInjectorProcessor: System prompt for agent '{agent_id}' processed. Placeholder '{self.PLACEHOLDER}' was handled with {chosen_format_str} descriptions.")
        return final_system_prompt
