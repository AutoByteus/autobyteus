# file: autobyteus/autobyteus/task_management/todo_list.py
"""
An in-memory implementation of a personal ToDoList for a single agent.
"""
import logging
from typing import List, Dict, Optional

from autobyteus.task_management.schemas import ToDoDefinitionSchema
from .todo import ToDo, ToDoStatus

logger = logging.getLogger(__name__)

class ToDoList:
    """
    An in-memory, list-based implementation of a personal ToDo list for an agent.
    It manages a collection of ToDo items.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.todos: List[ToDo] = []
        self._todo_map: Dict[str, ToDo] = {}
        self._id_counter: int = 0
        logger.info(f"ToDoList initialized for agent '{self.agent_id}'.")

    def _generate_next_id(self) -> str:
        self._id_counter += 1
        return f"todo_{self._id_counter:04d}"

    def add_todos(self, todo_definitions: List[ToDoDefinitionSchema]) -> List[ToDo]:
        """Creates and adds new to-do items from definitions, and returns the created items."""
        new_todos: List[ToDo] = []
        for definition in todo_definitions:
            new_id = self._generate_next_id()
            todo = ToDo(todo_id=new_id, **definition.model_dump())
            # This check is defensive, with a sequential counter it should not happen
            if todo.todo_id in self._todo_map:
                logger.warning(f"ToDo with ID '{todo.todo_id}' already exists in the list for agent '{self.agent_id}'. Skipping.")
                continue
            self.todos.append(todo)
            self._todo_map[todo.todo_id] = todo
            new_todos.append(todo)
        logger.info(f"Agent '{self.agent_id}': Added {len(new_todos)} new item(s) to the ToDoList.")
        return new_todos

    def add_todo(self, todo_definition: ToDoDefinitionSchema) -> ToDo:
        """Adds a single new to-do item from a definition."""
        created_todos = self.add_todos([todo_definition])
        return created_todos[0]

    def get_todo_by_id(self, todo_id: str) -> Optional[ToDo]:
        """Retrieves a to-do item by its ID."""
        return self._todo_map.get(todo_id)

    def update_todo_status(self, todo_id: str, status: ToDoStatus) -> bool:
        """Updates the status of a specific to-do item."""
        todo = self.get_todo_by_id(todo_id)
        if not todo:
            logger.warning(f"Agent '{self.agent_id}': Attempted to update status for non-existent todo_id '{todo_id}'.")
            return False
        
        old_status = todo.status
        todo.status = status
        logger.info(f"Agent '{self.agent_id}': Status of todo '{todo_id}' updated from '{old_status.value}' to '{status.value}'.")
        return True

    def get_all_todos(self) -> List[ToDo]:
        """Returns all to-do items."""
        return self.todos

    def clear(self) -> None:
        """Clears all to-do items from the list."""
        self.todos.clear()
        self._todo_map.clear()
        self._id_counter = 0
        logger.info(f"ToDoList for agent '{self.agent_id}' has been cleared.")
