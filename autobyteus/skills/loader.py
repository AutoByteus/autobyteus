import os
import logging
import re
from typing import Optional
from autobyteus.skills.model import Skill

logger = logging.getLogger(__name__)

class SkillLoader:
    """
    Responsible for loading and parsing SKILL.md files.
    Designed to be forgiving of minor formatting variations in LLM-generated content.
    """

    @staticmethod
    def load_skill(path: str) -> Skill:
        """
        Loads a skill from a given directory path.
        """
        if not os.path.isdir(path):
             raise FileNotFoundError(f"Skill directory not found: {path}")

        skill_file = os.path.join(path, "SKILL.md")
        if not os.path.exists(skill_file):
            raise FileNotFoundError(f"SKILL.md not found in {path}")

        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            raise IOError(f"Failed to read SKILL.md at {skill_file}: {e}")

        return SkillLoader._parse_skill(raw_content, path)

    @staticmethod
    def _parse_skill(raw_content: str, root_path: str) -> Skill:
        """
        Parses the content of a SKILL.md file. 
        Extracts metadata from the frontmatter block (delimited by ---).
        """
        # Extract the frontmatter block
        # Using a regex that is forgiving of whitespace around delimiters
        match = re.search(r'^\s*---\s*\n(.*?)\n\s*---\s*\n(.*)', raw_content, re.DOTALL | re.MULTILINE) 
        
        if not match:
            raise ValueError("Invalid SKILL.md format: Could not find frontmatter block delimited by '---'")

        frontmatter_text = match.group(1)
        body_content = match.group(2).strip()

        # Parse frontmatter lines (Key: Value)
        metadata = {}
        for line in frontmatter_text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower()] = value.strip()

        name = metadata.get("name")
        description = metadata.get("description")

        if not name:
            raise ValueError("Missing 'name' in SKILL.md metadata")
        if not description:
            raise ValueError("Missing 'description' in SKILL.md metadata")

        return Skill(
            name=name,
            description=description,
            content=body_content,
            root_path=root_path
        )
