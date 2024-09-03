from typing import Any

from autobyteus.workflow.task import Task

class Node:
    def __init__(self, task: Task):
        self.task = task

    async def execute(self, input_data: Any) -> Any:
        return await self.task.execute(input_data)

    def get_result(self) -> Any:
        return self.task.get_result()