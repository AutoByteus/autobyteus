# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_manifest_injector_processor.py
import logging
from typing import Dict, List, TYPE_CHECKING

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.registry import default_tool_registry, ToolDefinition
from autobyteus.tools.usage.providers import ToolManifestProvider

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


class ToolManifestInjectorProcessor(BaseSystemPromptProcessor):
    """
    Appends an 'Accessible Tools' section to the system prompt.
    Automatically determines XML or JSON format based on the LLM provider.
    """

    @classmethod
    def get_name(cls) -> str:
        return "ToolManifestInjector"

    @classmethod
    def get_order(cls) -> int:
        return 500

    @classmethod
    def is_mandatory(cls) -> bool:
        return True

    def __init__(self):
        self._manifest_provider = None

    def process(
        self,
        system_prompt: str,
        tool_instances: Dict[str, 'BaseTool'],
        agent_id: str,
        context: 'AgentContext'
    ) -> str:
        if not tool_instances:
            logger.info(f"Agent '{agent_id}': No tools configured. Skipping tool injection.")
            return system_prompt

        # Get LLM provider for format selection
        llm_provider = None
        if context.llm_instance and context.llm_instance.model:
            llm_provider = context.llm_instance.model.provider

        # Get tool definitions
        tool_definitions: List[ToolDefinition] = [
            td for name in tool_instances if (td := default_tool_registry.get_tool_definition(name))
        ]

        if not tool_definitions:
            logger.warning(f"Agent '{agent_id}': Tools configured but no definitions found in registry.")
            return system_prompt

        # Generate manifest
        try:
            if self._manifest_provider is None:
                self._manifest_provider = ToolManifestProvider()
            tools_manifest = self._manifest_provider.provide(
                tool_definitions=tool_definitions,
                provider=llm_provider,
            )
        except Exception as e:
            logger.exception(f"Agent '{agent_id}': Failed to generate tool manifest: {e}")
            return system_prompt

        # Append tools section
        tools_block = f"\n\n## Accessible Tools\n\n{tools_manifest}"
        logger.info(f"Agent '{agent_id}': Injected {len(tool_definitions)} tools.")
        return system_prompt + tools_block
