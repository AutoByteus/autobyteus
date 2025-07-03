# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_manifest_injector_processor.py
import logging
from typing import Dict, TYPE_CHECKING, List

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.usage.providers import ToolManifestProvider
from autobyteus.prompt.prompt_template import PromptTemplate

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ToolManifestInjectorProcessor(BaseSystemPromptProcessor):
    """
    Injects a tool manifest into the system prompt using Jinja2-style placeholders.
    It primarily targets the '{{tools}}' variable. It uses PromptTemplate for
    rendering and delegates manifest generation to a ToolManifestProvider.
    """
    # The '{{tools}}' placeholder is now handled by Jinja2 via PromptTemplate.
    DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT = "You have access to a set of tools. Use them by outputting the appropriate tool call format. The user can only see the output of the tool, not the call itself. The available tools are:\n\n"

    def __init__(self):
        self._manifest_provider = ToolManifestProvider()
        logger.debug(f"{self.get_name()} initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "ToolManifestInjector"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
        try:
            prompt_template = PromptTemplate(template=system_prompt)
        except Exception as e:
            logger.error(f"Failed to create PromptTemplate from system prompt for agent '{agent_id}'. Error: {e}", exc_info=True)
            # Return original prompt on Jinja2 parsing failure
            return system_prompt

        # Check if the 'tools' variable is actually in the template
        if "tools" not in prompt_template.required_vars:
            return system_prompt

        # Generate the manifest string for the 'tools' variable.
        tools_manifest: str
        if not tool_instances:
            logger.info(f"{self.get_name()}: The '{{{{tools}}}}' placeholder is present, but no tools are instantiated. Using 'No tools available.'")
            tools_manifest = "No tools available for this agent."
        else:
            tool_definitions: List[ToolDefinition] = [
                td for name in tool_instances if (td := default_tool_registry.get_tool_definition(name))
            ]

            llm_provider = context.llm_instance.model.provider if context.llm_instance and context.llm_instance.model else None

            try:
                # Delegate manifest generation to the provider
                tools_manifest = self._manifest_provider.provide(
                    tool_definitions=tool_definitions,
                    use_xml=context.config.use_xml_tool_format,
                    provider=llm_provider
                )
            except Exception as e:
                logger.exception(f"An unexpected error occurred during tool manifest generation for agent '{agent_id}': {e}")
                tools_manifest = "Error: Could not generate tool descriptions."
        
        # Check if the prompt *only* contains the 'tools' variable by rendering with an empty string
        rendered_without_tools = prompt_template.fill({"tools": ""})
        is_tools_only_prompt = not rendered_without_tools.strip()

        if is_tools_only_prompt:
             logger.info(f"{self.get_name()}: Prompt contains only the tools placeholder. Prepending default instructions.")
             return self.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT + tools_manifest
        else:
            # For prompts that contain other text, add a newline for better formatting before filling the template.
            tools_description_with_newline = f"\n{tools_manifest}"
            final_prompt = prompt_template.fill({"tools": tools_description_with_newline})
            return final_prompt
