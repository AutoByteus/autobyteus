# file: autobyteus/agent/system_prompt_processor/skill_injector_processor.py
import logging
from typing import TYPE_CHECKING

from .base_processor import BaseSystemPromptProcessor
from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.skills import load_skill_documents

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SkillInjectorProcessor(BaseSystemPromptProcessor):
    """Injects reusable skill documents into the system prompt."""

    def __init__(self):
        logger.debug("SkillInjectorProcessor initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "SkillInjector"

    @classmethod
    def get_order(cls) -> int:
        return 400

    @classmethod
    def is_mandatory(cls) -> bool:
        return False

    def process(
        self,
        system_prompt: str,
        tool_instances: dict[str, "BaseTool"],
        agent_id: str,
        context: "AgentContext",
    ) -> str:
        skill_paths = getattr(context.config, "skill_file_paths", None) or []
        if not skill_paths:
            return self._fill_placeholder(system_prompt, None)

        documents = load_skill_documents(skill_paths)
        if not documents:
            logger.warning("Agent '%s': No skills could be loaded. Leaving prompt unchanged.", agent_id)
            return self._fill_placeholder(system_prompt, None)

        blocks = [self._format_block(doc.name, doc.content, str(doc.skill_path)) for doc in documents]
        skills_block = "\n\n".join(blocks).strip()

        return self._fill_placeholder(system_prompt, skills_block)

    def _format_block(self, name: str, content: str, source_path: str) -> str:
        header = f"### Skill: {name}"
        footer = f"(source: {source_path})"
        body = content.strip()
        return f"{header}\n{body}\n{footer}"

    def _fill_placeholder(self, prompt: str, skills_block: str | None) -> str:
        try:
            prompt_template = PromptTemplate(template=prompt)
        except Exception as exc:
            logger.error("Failed to parse system prompt template: %s", exc, exc_info=True)
            # Fall back to appending skills text if available
            return self._append_block(prompt, skills_block)

        if "skills" not in prompt_template.required_vars:
            return self._append_block(prompt, skills_block)

        replacement = skills_block or "No additional skills configured."
        return prompt_template.fill({"skills": "\n" + replacement + "\n"})

    @staticmethod
    def _append_block(prompt: str, skills_block: str | None) -> str:
        if not skills_block:
            return prompt
        separator = "\n\n" if not prompt.endswith("\n") else "\n"
        return f"{prompt}{separator}{skills_block}\n"
