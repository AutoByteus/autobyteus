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
        
        # Build catalog (table of contents) for all skills
        catalog_entries = []
        detailed_sections = []

        for skill in all_skills:
            # Every skill goes in the catalog
            catalog_entries.append(f"- **{skill.name}**: {skill.description}")
            
            # Preloaded skills also get detailed content
            if skill.name in preloaded_skills_names:
                detailed_sections.append(
                    f"""#### {skill.name}
**Root Path:** `{skill.root_path}`

{skill.content}""")

        # Build the skills block
        skills_block = "\n\n## Agent Skills\n"
        
        # Catalog section (like table of contents)
        skills_block += "### Skill Catalog\n"
        skills_block += "\n".join(catalog_entries) + "\n"
        skills_block += "\nTo load a skill not shown in detail below, use the `load_skill` tool.\n"
        
        # Critical rules section (applies to ALL skills)
        if detailed_sections:
            skills_block += """
### Critical Rules for Using Skills

> **Path Resolution Required for Skill Files**
> 
> Skill instructions use relative paths (e.g., `./scripts/run.sh` or `scripts/run.sh`) to refer to internal files.
> However, standard tools resolve relative paths against the User's Workspace, not the skill directory.
> 
> When using ANY file from a skill, you MUST convert its path to ABSOLUTE:
> `Root Path` + `Relative Path` = `Absolute Path`
> 
> **Examples:**
> 1. Root Path: `/path/to/skill`
>    Relative: `./scripts/run.sh`
>    Result: `/path/to/skill/scripts/run.sh`
> 
> 2. Root Path: `/path/to/skill`
>    Relative: `scripts/run.sh`
>    Result: `/path/to/skill/scripts/run.sh`

"""
        
        # Detailed content section (like reading specific chapters)
        if detailed_sections:
            skills_block += "### Skill Details\n"
            skills_block += "\n".join(detailed_sections) + "\n"

        logger.info(f"Agent '{agent_id}': Injected {len(catalog_entries)} skills in catalog, {len(detailed_sections)} with details.")
        return system_prompt + skills_block
