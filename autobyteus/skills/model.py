from dataclasses import dataclass

@dataclass
class Skill:
    """
    Represents a loaded skill.
    """
    name: str
    description: str
    content: str  # The body of the SKILL.md file
    root_path: str  # The absolute path to the skill directory
