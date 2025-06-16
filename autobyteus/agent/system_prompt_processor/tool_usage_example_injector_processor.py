# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_usage_example_injector_processor.py
import logging
import json
from typing import Dict, Any, TYPE_CHECKING, List

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.registry import default_tool_registry, ToolDefinition

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolUsageExampleInjectorProcessor(BaseSystemPromptProcessor):
    """
    Injects tool usage examples into the system prompt, replacing '{{tool_examples}}'.
    """
    PLACEHOLDER = "{{tool_examples}}"
    XML_EXAMPLES_HEADER = "## Tool Usage Examples (XML Format):\n"
    JSON_EXAMPLES_HEADER = "## Tool Usage Examples (JSON Format):\n"
    DEFAULT_NO_TOOLS_MESSAGE = "No tool examples are available as no tools are configured for this agent."
    
    def get_name(self) -> str:
        return "ToolUsageExampleInjector"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
        if self.PLACEHOLDER not in system_prompt:
            return system_prompt

        if not tool_instances:
            logger.info(f"{self.get_name()}: No tools available for agent '{agent_id}'. Injecting no-tools message.")
            return system_prompt.replace(self.PLACEHOLDER, self.DEFAULT_NO_TOOLS_MESSAGE)

        # Gather tool definitions from the registry
        tool_definitions: List[ToolDefinition] = []
        for name in tool_instances.keys():
            definition = default_tool_registry.get_tool_definition(name)
            if definition:
                tool_definitions.append(definition)
            else:
                logger.warning(f"Could not find ToolDefinition for tool '{name}' in the registry. It will be excluded from the examples.")

        examples_string = ""
        
        # --- Start of Bug Fix ---
        # The provider is on the model, which is on the llm_instance in the context.
        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider
        else:
            logger.warning(f"Agent '{agent_id}': LLM instance or model not available in context. Cannot determine provider for tool example formatting.")
        # --- End of Bug Fix ---

        try:
            if context.config.use_xml_tool_format:
                example_parts = []
                for td in tool_definitions:
                    try:
                        # Correctly passing the provider
                        xml_example = td.get_usage_xml_example(provider=llm_provider)
                        if xml_example:
                            example_parts.append(xml_example)
                        else:
                            logger.warning(f"Tool '{td.name}' returned an empty XML example string.")
                            example_parts.append(f'<!-- Error generating XML example for tool: {td.name} (empty result) -->')
                    except Exception as e:
                        logger.error(f"Failed to generate XML example for tool '{td.name}': {e}", exc_info=True)
                        example_parts.append(f'<!-- Error generating XML example for tool: {td.name} -->')
                
                inner_content = "\n\n".join(example_parts)
                examples_string = f"{self.XML_EXAMPLES_HEADER}<tool_calls>\n{inner_content}\n</tool_calls>"
            else: # JSON Format
                json_example_parts = []
                for td in tool_definitions:
                    try:
                        # Correctly passing the provider
                        json_example = td.get_usage_json_example(provider=llm_provider)
                        if json_example:
                            json_example_parts.append(json.dumps(json_example, indent=2))
                        else:
                            logger.warning(f"Tool '{td.name}' returned an empty JSON example.")
                            json_example_parts.append(f'// Error generating JSON example for tool: {td.name} (empty result)')
                    except Exception as e:
                        logger.error(f"Failed to generate JSON example for tool '{td.name}': {e}", exc_info=True)
                        json_example_parts.append(f'// Error generating JSON example for tool: {td.name}')
                
                inner_content = ",\n".join(json_example_parts)
                examples_string = f"{self.JSON_EXAMPLES_HEADER}[\n{inner_content}\n]"
        except Exception as e:
            logger.exception(f"An unexpected error occurred during tool example generation for agent '{agent_id}': {e}")
            examples_string = "Error: Could not generate tool usage examples."

        return system_prompt.replace(self.PLACEHOLDER, examples_string)
