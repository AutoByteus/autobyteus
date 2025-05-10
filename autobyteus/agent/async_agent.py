import asyncio
import logging
from typing import (
    List, 
    Optional, 
    AsyncGenerator, 
    Any, 
    NoReturn,
    Union,
    AsyncIterator
)
from autobyteus.agent.agent import Agent
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus
from autobyteus.conversation.user_message import UserMessage
from autobyteus.agent.tool_invocation import ToolInvocation

logger = logging.getLogger(__name__)

class AsyncAgent(Agent):
    """
    An asynchronous agent that supports streaming LLM responses while maintaining
    compatibility with the base agent functionality.
    """
    
    def __init__(
        self, 
        role: str, 
        llm: BaseLLM, 
        tools: Optional[List[BaseTool]] = None,
        agent_id: Optional[str] = None
    ) -> None:
        """
        Initialize the AsyncAgent with the given parameters.

        Args:
            role: The role of the agent
            llm: The language model instance
            tools: List of available tools
            agent_id: Optional unique identifier for the agent
        """
        super().__init__(
            role, 
            llm, 
            tools, 
            agent_id
        )

    async def handle_user_messages(self) -> NoReturn:
        """
        Handle incoming user messages continuously.
        Processes messages using streaming responses.
        """
        logger.info(f"Agent {self.role} started handling user messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                user_message: UserMessage = await asyncio.wait_for(
                    self.user_messages.get(), 
                    timeout=1.0
                )
                logger.info(f"Agent {self.role} handling user message")
                await self.process_streaming_response(
                    self.llm.stream_user_message(user_message)
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"User message handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling user message for agent {self.role}: {str(e)}")

    async def handle_tool_result_messages(self) -> NoReturn:
        """
        Handle tool execution result messages continuously.
        Processes messages using streaming responses.
        """
        logger.info(f"Agent {self.role} started handling tool result messages")
        while not self.task_completed.is_set() and self.status == AgentStatus.RUNNING:
            try:
                message: str = await asyncio.wait_for(
                    self.tool_result_messages.get(), 
                    timeout=1.0
                )
                logger.info(f"Agent {self.role} handling tool result message: {message}")
                tool_result_message = UserMessage(content=f"Tool execution result: {message}")
                await self.process_streaming_response(
                    self.llm.stream_user_message(tool_result_message)
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info(f"Tool result handler for agent {self.role} cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling tool result for agent {self.role}: {str(e)}")

    async def process_streaming_response(
        self, 
        response_stream: AsyncIterator[str]
    ) -> None:
        """
        Process streaming responses from the LLM, emitting each chunk and handling
        tool invocations after receiving the complete response.
        
        Args:
            response_stream: AsyncIterator yielding response tokens
        """
        complete_response: str = ""
        try:
            async for chunk in response_stream:
                # Emit each chunk as it arrives
                self.emit(
                    EventType.ASSISTANT_RESPONSE, 
                    response=chunk,
                    is_complete=False
                )
                complete_response += chunk
            # Emit the complete response
            self.emit(
                EventType.ASSISTANT_RESPONSE, 
                response=complete_response,
                is_complete=True
            )

            if self.tools and self.tool_usage_response_parser:
                tool_invocation: ToolInvocation = self.tool_usage_response_parser.parse_response(complete_response)
                if tool_invocation.is_valid():
                    await self.execute_tool(tool_invocation)
                    return

            logger.info(f"Assistant response for agent {self.role}: {complete_response}")

        except Exception as e:
            logger.error(f"Error processing streaming response for agent {self.role}: {str(e)}")
            self.emit(
                EventType.ERROR,
                error=str(e))
