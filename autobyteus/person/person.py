from typing import List
from autobyteus.person.role import Role

class Person:
    def __init__(self, name: str, role: Role, characteristics: List[str]):
        self.name = name
        self.role = role
        self.characteristics = characteristics
        self.tasks = []

    def get_description(self) -> str:
        characteristics_str = ", ".join(self.characteristics)
        return (f"Person: {self.name}\n"
                f"{self.role.get_description()}\n"
                f"Characteristics: {characteristics_str}")

    def __str__(self) -> str:
        return f"{self.name} ({self.role.name})"

    def assign_task(self, task):
        if task not in self.tasks:
            self.tasks.append(task)

    def unassign_task(self, task):
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self):
        return self.tasks