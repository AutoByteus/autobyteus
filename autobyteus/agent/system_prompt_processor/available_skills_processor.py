import logging
from typing import TYPE_CHECKING, Dict
from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.skills.registry import SkillRegistry

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class AvailableSkillsProcessor(BaseSystemPromptProcessor):
    """
    A system prompt processor that injects information about available skills.
    For preloaded skills (defined in config), it injects the full map.
    For other skills, it injects a summary (awareness).
    """

    def process(self,
                system_prompt: str,
                tool_instances: Dict[str, 'BaseTool'],
                agent_id: str,
                context: 'AgentContext') -> str:
        registry = SkillRegistry()
        all_skills = registry.list_skills()
        
        if not all_skills:
            logger.debug(f"Agent '{agent_id}': No skills found in registry. Skipping injection.")
            return system_prompt

        # Preloaded skills from config
        preloaded_skills_names = getattr(context.config, 'skills', [])
        
        preloaded_sections = []
        available_summaries = []

        for skill in all_skills:
            if skill.name in preloaded_skills_names:
                preloaded_sections.append(
                    f"""## Skill: {skill.name}
Root Path: {skill.root_path}

> **CRITICAL: Path Resolution When Using Tools**
> 
> This skill uses relative paths. When using any tool that requires a file path,
> you MUST first construct the full absolute path by combining the Root Path above
> with the relative path from the skill instructions.
> 
> **Example:** Root Path + `./scripts/format.sh` = `{skill.root_path}/scripts/format.sh`

{skill.content}""")
            else:
                available_summaries.append(f"- {skill.name}: {skill.description}")

        skills_block = "\n\n## Agent Skills\n"
        
        if preloaded_sections:
            skills_block += "### Preloaded Skills (Immediate Context)\n"
            skills_block += "\n".join(preloaded_sections) + "\n"

        if available_summaries:
            skills_block += "### Available Skills (Load on demand using 'load_skill')\n"
            skills_block += "If you need one of these skills, use the 'load_skill' tool to retrieve its detailed map and assets.\n"
            skills_block += "\n".join(available_summaries) + "\n"

        logger.info(f"Agent '{agent_id}': Injected {len(preloaded_sections)} preloaded and {len(available_summaries)} available skill(s) into system prompt.")
        return system_prompt + skills_block
