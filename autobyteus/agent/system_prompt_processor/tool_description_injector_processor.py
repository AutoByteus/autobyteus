# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_description_injector_processor.py
import logging
import json
from typing import Dict, TYPE_CHECKING, List

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.registry import default_tool_registry, ToolDefinition

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolDescriptionInjectorProcessor(BaseSystemPromptProcessor):
    """
    Injects tool descriptions into the system prompt, replacing '{{tools}}'.
    """
    PLACEHOLDER = "{{tools}}"
    DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT = "The user has access to a set of tools. Use them by outputting a JSON object with a 'tool_code' key, where the value is a single-line XML string of the tool call. The user can only see the output of the tool, not the call itself. The available tools are:\n"

    def get_name(self) -> str:
        return "ToolDescriptionInjector"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
        if self.PLACEHOLDER not in system_prompt:
            return system_prompt

        is_tools_only_prompt = system_prompt.strip() == self.PLACEHOLDER
        
        if not tool_instances:
            logger.info(f"{self.get_name()}: The '{self.PLACEHOLDER}' placeholder is present, but no tools are instantiated. Replacing with 'No tools available.'")
            replacement_text = "No tools available for this agent."
            if is_tools_only_prompt:
                logger.info(f"{self.get_name()}: Prompt contains only the tools placeholder. Prepending default instructions.")
                return self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + replacement_text
            return system_prompt.replace(self.PLACEHOLDER, f"\n{replacement_text}")

        # Gather tool definitions from the registry
        tool_definitions: List[ToolDefinition] = []
        for name in tool_instances.keys():
            definition = default_tool_registry.get_tool_definition(name)
            if definition:
                tool_definitions.append(definition)
            else:
                logger.warning(f"Could not find ToolDefinition for tool '{name}' in the registry. It will be excluded from the prompt.")

        tools_description = ""
        
        # --- Start of Bug Fix ---
        # The provider is on the model, which is on the llm_instance in the context.
        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider
        else:
            logger.warning(f"Agent '{agent_id}': LLM instance or model not available in context. Cannot determine provider for tool description formatting.")
        # --- End of Bug Fix ---

        try:
            if context.config.use_xml_tool_format:
                schema_parts = []
                for td in tool_definitions:
                    try:
                        # Correctly passing the provider
                        usage_xml = td.get_usage_xml(provider=llm_provider)
                        if usage_xml:
                            schema_parts.append(usage_xml)
                        else:
                            logger.warning(f"Tool '{td.name}' for agent '{agent_id}' returned empty usage XML description.")
                            schema_parts.append(f'<tool_error name="{td.name}">Error: Usage information is empty for this tool.</tool_error>')
                    except Exception as e:
                        logger.error(f"Failed to get usage XML for tool '{td.name}' for agent '{agent_id}': {e}", exc_info=True)
                        schema_parts.append(f'<tool_error name="{td.name}">Error: Usage information could not be generated for this tool.</tool_error>')
                
                inner_content = "\n".join(schema_parts)
                tools_description = f"<tools>\n{inner_content}\n</tools>"
            else: # JSON format
                schema_parts = []
                for td in tool_definitions:
                    try:
                        # Correctly passing the provider
                        usage_json = td.get_usage_json(provider=llm_provider)
                        if usage_json:
                             schema_parts.append(json.dumps(usage_json, indent=2))
                        else:
                            logger.warning(f"Tool '{td.name}' for agent '{agent_id}' returned empty usage JSON description.")
                            schema_parts.append(json.dumps({"tool_error": {"name": td.name, "message": "Error: Usage information is empty for this tool."}}))
                    except Exception as e:
                        logger.error(f"Failed to get usage JSON for tool '{td.name}' for agent '{agent_id}': {e}", exc_info=True)
                        schema_parts.append(json.dumps({"tool_error": {"name": td.name, "message": "Error: Usage information could not be generated for this tool."}}))
                
                tools_description = "\n".join(schema_parts)
        except Exception as e:
            logger.exception(f"An unexpected error occurred during tool description generation for agent '{agent_id}': {e}")
            tools_description = "Error: Could not generate tool descriptions."
        
        final_replacement_text = f"\n{tools_description}"
        if is_tools_only_prompt:
             logger.info(f"{self.get_name()}: Prompt contains only the tools placeholder. Prepending default instructions.")
             return self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + tools_description

        return system_prompt.replace(self.PLACEHOLDER, final_replacement_text)
