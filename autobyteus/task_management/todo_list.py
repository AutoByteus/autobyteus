# file: autobyteus/autobyteus/task_management/todo_list.py
"""
An in-memory implementation of a personal ToDoList for a single agent.
"""
import logging
from typing import List, Dict, Optional

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
        logger.info(f"ToDoList initialized for agent '{self.agent_id}'.")

    def add_todos(self, todos: List[ToDo]) -> bool:
        """Adds new to-do items to the list."""
        for todo in todos:
            if todo.todo_id in self._todo_map:
                logger.warning(f"ToDo with ID '{todo.todo_id}' already exists in the list for agent '{self.agent_id}'. Skipping.")
                continue
            self.todos.append(todo)
            self._todo_map[todo.todo_id] = todo
        logger.info(f"Agent '{self.agent_id}': Added {len(todos)} new item(s) to the ToDoList.")
        return True

    def add_todo(self, todo: ToDo) -> bool:
        """Adds a single new to-do item to the list."""
        return self.add_todos([todo])

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
        logger.info(f"ToDoList for agent '{self.agent_id}' has been cleared.")
