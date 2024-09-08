"""
task.py: Contains the Task class for representing individual tasks within a workflow.

This module defines the Task class, which encapsulates the functionality for a single task,
including its objective, input and output descriptions, associated tools, LLM integration,
and execution logic using a dynamically created Agent.
"""

import asyncio
from typing import Any, List, Optional
from autobyteus.persona.persona import Persona
from autobyteus.tools.base_tool import BaseTool
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.agent.agent import StandaloneAgent
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.conversation.persistence.file_based_persistence_provider import FileBasedPersistenceProvider

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
        agent = self._create_agent()
        prompt = self._generate_agent_prompt(input_data)
        
        # Set the initial prompt for the agent
        agent.prompt_builder.set_variable_value("initial_prompt", prompt)
        
        # Run the agent
        await agent.run()
        
        # Retrieve the result from the agent's conversation
        self.result = agent.conversation.get_last_assistant_message()
        return self.result

    def _create_agent(self) -> StandaloneAgent:
        prompt_builder = PromptBuilder()
        agent_id = f"task_{self.objective[:10]}_{id(self)}"
        return StandaloneAgent(
            role=f"Task_{self.objective[:20]}",
            prompt_builder=prompt_builder,
            llm=self.llm,
            tools=self.tools,
            use_xml_parser=True,
            persistence_provider_class=FileBasedPersistenceProvider,
            agent_id=agent_id
        )

    def _generate_agent_prompt(self, input_data: Any) -> str:
        prompt = f"""
        You are an AI agent tasked with executing the following objective:
        {self.objective}

        Input Description: {self.input_description}
        Output Description: {self.output_description}
        Workflow Description: {self.workflow_description}

        Your persona: {self.persona}

        Input Data: {input_data}

        You have access to the following tools:
        {self._format_tools()}

        Please execute the task step by step, using the tools when necessary.
        Provide your final output when the task is completed.
        """
        return prompt

    def _format_tools(self) -> str:
        return "\n".join([f"- {tool.get_name()}: {tool.get_description()}" for tool in self.tools])

    def get_result(self) -> Any:
        return self.result

    def add_subtask(self, subtask: 'Task'):
        self.subtasks.append(subtask)