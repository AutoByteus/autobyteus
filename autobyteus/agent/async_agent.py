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
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.events.event_types import EventType
from autobyteus.agent.status import AgentStatus
from autobyteus.conversation.user_message import UserMessage
from autobyteus.conversation.conversation import Conversation
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
        agent_id: Optional[str] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        initial_user_message: Optional[UserMessage] = None
    ) -> None:
        """
        Initialize the AsyncAgent with the given parameters.

        Args:
            role: The role of the agent
            llm: The language model instance
            tools: List of available tools
            use_xml_parser: Whether to use XML parser for responses
            agent_id: Optional unique identifier for the agent
            prompt_builder: Optional prompt builder instance
            initial_user_message: Optional initial message to start the conversation
        """
        super().__init__(
            role, 
            llm, 
            tools, 
            agent_id, 
            prompt_builder, 
            initial_user_message
        )

    async def initialize_conversation(self) -> None:
        """Initialize the conversation with initial message or prompt."""
        logger.info(f"Initializing conversation for agent: {self.role}")
        self.conversation = Conversation(self.llm)

        if self.initial_user_message:
            initial_message = self.initial_user_message
        else:
            prompt_content = self.prompt_builder.set_variable_value(
                "external_tools", 
                self._get_external_tools_section()
            ).build()
            initial_message = UserMessage(content=prompt_content)

        logger.debug(f"Initial user message for agent {self.role}: {initial_message}")
        await self.process_streaming_response(
            self.conversation.stream_user_message(
                initial_message.content, 
                initial_message.file_paths
            )
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
                    self.conversation.stream_user_message(
                        user_message.content, 
                        user_message.file_paths
                    )
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
                await self.process_streaming_response(
                    self.conversation.stream_user_message(
                        f"Tool execution result: {message}"
                    )
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