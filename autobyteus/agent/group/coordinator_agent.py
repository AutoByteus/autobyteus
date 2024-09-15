# File: autobyteus/agent/group/coordinator_agent.py

import asyncio
import os
import logging
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent, AgentStatus
from autobyteus.agent.message.message_types import MessageType
from autobyteus.agent.message.message import Message

from autobyteus.events.event_types import EventType
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.llm.base_llm import BaseLLM
from typing import List
from autobyteus.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class CoordinatorAgent(GroupAwareAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"CoordinatorAgent initialized with role: {self.role}")


    async def process_llm_response(self, llm_response):
        """
        Process the LLM response for the CoordinatorAgent.
        """
        logger.info(f"CoordinatorAgent {self.role} processing LLM response")
        tool_invocation = self.response_parser.parse_response(llm_response)

        if tool_invocation.is_valid():
            await self.execute_tool(tool_invocation)
        else:
            logger.info(f"Coordinator Response for agent {self.role}: {llm_response}")
            logger.info(f"CoordinatorAgent {self.role} task completed, emitting TASK_COMPLETED event")
            self.emit(EventType.TASK_COMPLETED)
