from typing import List
from autobyteus.persona.role import Role

class Persona:
    def __init__(self, name: str, role: Role, characteristics: List[str]):
        self.name = name
        self.role = role
        self.characteristics = characteristics

    def get_description(self) -> str:
        characteristics_str = ", ".join(self.characteristics)
        return (f"Persona: {self.name}\n"
                f"{self.role.get_description()}\n"
                f"Characteristics: {characteristics_str}")

    def __str__(self) -> str:
        return f"{self.name} ({self.role.name})"