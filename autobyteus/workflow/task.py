from typing import Any, List, Optional
from autobyteus.tools.base_tool import BaseTool
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.persona import Persona  # We'll update this import path later

class Task:
    def __init__(
        self,
        objective: str,
        input_description: str,
        output_description: str,
        workflow_description: Optional[str],
        tools: List[BaseTool],
        llm: BaseLLM,
        persona: Persona,
        subtasks: Optional[List['Task']] = None
    ):
        self.objective = objective
        self.input_description = input_description
        self.output_description = output_description
        self.workflow_description = workflow_description
        self.tools = tools
        self.llm = llm
        self.persona = persona
        self.subtasks = subtasks or []
        self.result = None

    async def execute(self, input_data: Any) -> Any:
        if self.subtasks:
            return await self._execute_subtasks(input_data)
        else:
            return await self._execute_single_task(input_data)

    async def _execute_subtasks(self, input_data: Any) -> Any:
        result = input_data
        for subtask in self.subtasks:
            print(f"Executing subtask: {subtask.objective}")
            result = await subtask.execute(result)
        self.result = result
        return self.result

    async def _execute_single_task(self, input_data: Any) -> Any:
        llm_response = await self.llm.generate(
            f"Objective: {self.objective}, Input: {input_data}, Persona: {self.persona}"
        )
        tool_results = [await tool._execute(input_data) for tool in self.tools]
        self.result = f"Task result: {llm_response}, Tool results: {tool_results}"
        return self.result

    def get_result(self) -> Any:
        return self.result

    def add_subtask(self, subtask: 'Task'):
        self.subtasks.append(subtask)