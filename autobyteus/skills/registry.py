import os
import logging
from typing import Dict, List, Optional
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.skills.model import Skill
from autobyteus.skills.loader import SkillLoader

logger = logging.getLogger(__name__)

class SkillRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for managing and discovering agent skills.
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        logger.info("SkillRegistry initialized.")

    def register_skill_from_path(self, path: str) -> Skill:
        """
        Loads a skill from the given path and registers it.
        If a skill with the same name already exists, it will be overwritten.
        """
        try:
            skill = SkillLoader.load_skill(path)
            self._skills[skill.name] = skill
            logger.info(f"Skill '{skill.name}' registered from path: {path}")
            return skill
        except Exception as e:
            logger.error(f"Failed to register skill from path '{path}': {e}")
            raise

    def discover_skills(self, directory_path: str):
        """
        Scans a directory for skill subdirectories (those containing SKILL.md) 
        and registers them.
        """
        if not os.path.isdir(directory_path):
            logger.warning(f"Discovery directory not found: {directory_path}")
            return

        logger.debug(f"Discovering skills in: {directory_path}")
        for entry in os.scandir(directory_path):
            if entry.is_dir():
                skill_md_path = os.path.join(entry.path, "SKILL.md")
                if os.path.exists(skill_md_path):
                    try:
                        self.register_skill_from_path(entry.path)
                    except Exception:
                        # Continue discovering other skills even if one fails
                        continue

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        Retrieves a skill by its name.
        """
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        """
        Returns a list of all registered skills.
        """
        return list(self._skills.values())

    def clear(self):
        """
        Clears all registered skills. Primarily for testing.
        """
        self._skills.clear()
        logger.debug("SkillRegistry cleared.")
