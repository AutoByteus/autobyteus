"""
workflow.py: Contains the Workflow class for managing a sequence of tasks.

This module defines the Workflow class, which represents a series of tasks to be executed in order.
The Workflow class allows adding tasks, executing the entire workflow, and retrieving the final result.
"""

from typing import List, Any
from autobyteus.workflow.task import Task

class Workflow:
    def __init__(self):
        """
        Initialize a new Workflow instance with an empty list of tasks.
        """
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        """
        Add a new task to the workflow.

        Args:
            task (Task): The task to be added to the workflow.
        """
        self.tasks.append(task)

    async def execute(self, input_data: Any) -> Any:
        """
        Execute all tasks in the workflow sequentially.

        Args:
            input_data (Any): The initial input data for the first task.

        Returns:
            Any: The result of the final task in the workflow.
        """
        result = input_data
        for task in self.tasks:
            result = await task.execute(result)
        return result

    def get_result(self) -> Any:
        """
        Get the result of the last task in the workflow.

        Returns:
            Any: The result of the last task, or None if there are no tasks.
        """
        return self.tasks[-1].get_result() if self.tasks else None