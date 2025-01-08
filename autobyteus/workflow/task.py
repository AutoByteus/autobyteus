"""
task.py: Contains the Task class for representing individual tasks within a workflow.

This module defines the Task class, which encapsulates the functionality for a single task,
including its objective, input and output descriptions, associated tools, LLM integration,
and execution logic using a dynamically created Agent.
"""

from typing import Any, List, Optional
from autobyteus.tools.base_tool import BaseTool
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.agent import Agent
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.person.person import Person

class Task:
    def __init__(
        self,
        description: str,
        objective: str,
        input_description: str,
        expected_output_description: str,
        workflow_description: Optional[str],
        tools: List[BaseTool],
        llm: BaseLLM,
        person: Optional[Person] = None,
        subtasks: Optional[List['Task']] = None
    ):
        self.description = description
        self.objective = objective
        self.input_description = input_description
        self.expected_output_description = expected_output_description
        self.workflow_description = workflow_description
        self.tools = tools
        self.llm = llm
        self.person = None
        if person:
            self.assign_to(person)
        self.subtasks = subtasks or []
        self.result = None

    def assign_to(self, person: Person):
        if self.person:
            self.person.unassign_task(self)
        self.person = person
        person.assign_task(self)

    def unassign(self):
        if self.person:
            self.person.unassign_task(self)
            self.person = None

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
        agent = self._create_agent()
        
        # Set the variable values for the prompt
        agent.prompt_builder.set_variable_value("name", self.person.name)
        agent.prompt_builder.set_variable_value("role", self.person.role.name)
        agent.prompt_builder.set_variable_value("person_description", self.person.get_description())
        agent.prompt_builder.set_variable_value("task_description", self.description)
        agent.prompt_builder.set_variable_value("objective", self.objective)
        agent.prompt_builder.set_variable_value("input_description", self.input_description)
        agent.prompt_builder.set_variable_value("expected_output_description", self.expected_output_description)
        agent.prompt_builder.set_variable_value("workflow_description", self.workflow_description)
        agent.prompt_builder.set_variable_value("tools", self._format_tools())
        agent.prompt_builder.set_variable_value("input_data", str(input_data))
        
        # Run the agent
        await agent.run()
        
        # Retrieve the result from the agent's conversation
        self.result = agent.conversation.get_last_assistant_message()
        return self.result

    def _create_agent(self) -> Agent:
        agent_id = f"task_{self.objective[:10]}_{id(self)}"
        
        # Generate the initial prompt
        initial_prompt = self._generate_initial_prompt()
        
        return Agent(
            role=f"Task_{self.objective[:20]}",
            llm=self.llm,
            tools=self.tools,
            use_xml_parser=True,
            agent_id=agent_id,
            initial_user_message=initial_prompt
        )

    def _generate_initial_prompt(self) -> str:
        template = """
        You are {name}. Your role is {role}.

        {person_description}

        Task Description: {task_description}
        Objective: {objective}

        Input Description: {input_description}
        Expected Output: {expected_output_description}

        Workflow:
        {workflow_description}

        Available Tools:
        {tools}

        Input Data:
        {input_data}

        Please complete the task based on the given information and using the available tools.
        """
        prompt_builder = PromptBuilder.from_string(template)
        prompt_builder.set_variable_value("name", self.person.name)
        prompt_builder.set_variable_value("role", self.person.role.name)
        prompt_builder.set_variable_value("person_description", self.person.get_description())
        prompt_builder.set_variable_value("task_description", self.description)
        prompt_builder.set_variable_value("objective", self.objective)
        prompt_builder.set_variable_value("input_description", self.input_description)
        prompt_builder.set_variable_value("expected_output_description", self.expected_output_description)
        prompt_builder.set_variable_value("workflow_description", self.workflow_description)
        prompt_builder.set_variable_value("tools", self._format_tools())
        prompt_builder.set_variable_value("input_data", "To be provided during execution")
        return prompt_builder.build()

    def _format_tools(self) -> str:
        return "\n".join([f"- {tool.get_name()}: {tool.get_description()}" for tool in self.tools])

    def get_result(self) -> Any:
        return self.result

    def add_subtask(self, subtask: 'Task'):
        self.subtasks.append(subtask)
