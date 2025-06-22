# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_manifest_injector_processor.py
import logging
from typing import Dict, TYPE_CHECKING, List

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.usage.providers import ToolManifestProvider

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolManifestInjectorProcessor(BaseSystemPromptProcessor):
    """
    Injects a tool manifest into the system prompt, replacing '{{tools}}'.
    It delegates the generation of the manifest string to a ToolManifestProvider.
    """
    PLACEHOLDER = "{{tools}}"
    DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT = "You have access to a set of tools. Use them by outputting the appropriate tool call format. The user can only see the output of the tool, not the call itself. The available tools are:\n\n"

    def __init__(self):
        self._manifest_provider = ToolManifestProvider()
        logger.debug(f"{self.get_name()} initialized.")

    def get_name(self) -> str:
        return "ToolManifestInjector"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
        if self.PLACEHOLDER not in system_prompt:
            return system_prompt

        is_tools_only_prompt = system_prompt.strip() == self.PLACEHOLDER
        
        if not tool_instances:
            logger.info(f"{self.get_name()}: The '{self.PLACEHOLDER}' placeholder is present, but no tools are instantiated. Replacing with 'No tools available.'")
            replacement_text = "No tools available for this agent."
            if is_tools_only_prompt:
                return self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + replacement_text
            return system_prompt.replace(self.PLACEHOLDER, f"\n{replacement_text}")

        tool_definitions: List[ToolDefinition] = [
            td for name in tool_instances if (td := default_tool_registry.get_tool_definition(name))
        ]

        llm_provider = context.llm_instance.model.provider if context.llm_instance and context.llm_instance.model else None

        try:
            # Delegate manifest generation to the provider
            tools_description = self._manifest_provider.provide(
                tool_definitions=tool_definitions,
                use_xml=context.config.use_xml_tool_format,
                provider=llm_provider
            )
        except Exception as e:
            logger.exception(f"An unexpected error occurred during tool manifest generation for agent '{agent_id}': {e}")
            tools_description = "Error: Could not generate tool descriptions."
        
        final_replacement_text = f"\n{tools_description}"
        if is_tools_only_prompt:
             logger.info(f"{self.get_name()}: Prompt contains only the tools placeholder. Prepending default instructions.")
             return self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + tools_description

        return system_prompt.replace(self.PLACEHOLDER, final_replacement_text)
