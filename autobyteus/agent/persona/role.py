from typing import List

class Role:
    def __init__(self, name: str, skills: List[str], responsibilities: List[str]):
        self.name = name
        self.skills = skills
        self.responsibilities = responsibilities

    def get_description(self) -> str:
        skills_str = ", ".join(self.skills)
        responsibilities_str = ", ".join(self.responsibilities)
        return (f"Role: {self.name}\n"
                f"Skills: {skills_str}\n"
                f"Responsibilities: {responsibilities_str}")