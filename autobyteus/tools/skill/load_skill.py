import logging
from typing import TYPE_CHECKING
from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.skills.registry import SkillRegistry

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="load_skill", category=ToolCategory.GENERAL)
async def load_skill(context: 'AgentContext', skill_name: str) -> str:
    """
    Loads a skill's entry point (SKILL.md) and provides its root path context.
    Use this to understand a specialized skill's capabilities and internal assets.
    
    Args:
        skill_name: The registered name of the skill (e.g., 'java_expert') or a path to a skill directory.
    
    Returns:
        A formatted context block containing the skill's map, its absolute root path, and path resolution guidance.
    """
    logger.debug(f"Tool 'load_skill' called for skill: {skill_name}")
    registry = SkillRegistry()
    skill = registry.get_skill(skill_name)
    
    if not skill:
        # Fallback: check if skill_name is actually a path
        logger.debug(f"Skill '{skill_name}' not found in registry. Attempting to register from path.")
        try:
            skill = registry.register_skill_from_path(skill_name)
        except Exception as e:
            error_msg = f"Skill '{skill_name}' not found and is not a valid skill path: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    logger.info(f"Skill '{skill.name}' successfully loaded.")
    return f"""## Skill: {skill.name}
Root Path: {skill.root_path}

> **CRITICAL: Path Resolution When Using Tools**
> 
> This skill uses relative paths. When using any tool that requires a file path,
> you MUST first construct the full absolute path by combining the Root Path above
> with the relative path from the skill instructions.
> 
> **Example:** Root Path + `./scripts/format.sh` = `{skill.root_path}/scripts/format.sh`

{skill.content}"""