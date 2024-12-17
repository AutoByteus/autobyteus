import asyncio
import logging
from typing import Optional, Callable, Any, List

from autobyteus.agent.agent import StandaloneAgent
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.events.event_types import EventType
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.conversation.user_message import UserMessage

logger = logging.getLogger(__name__)

class SimpleTask(EventEmitter):
    """
    A simplified task execution class focusing on single instruction tasks
    with minimal configuration, built-in result retrieval, and optional file inputs.
    """
    def __init__(
        self, 
        llm: BaseLLM, 
        instruction: str, 
        output_parser: Optional[Callable[[str], Any]] = None,
        role: str = "SimpleTask",
        file_paths: Optional[List[str]] = None
    ):
        """
        Initialize a SimpleTask with optional file paths.

        Args:
            llm (BaseLLM): Language model to use for task execution
            instruction (str): Task instruction or prompt
            output_parser (Optional[Callable]): Optional function to parse output
            role (str, optional): Role description for the task. Defaults to "SimpleTask".
            file_paths (Optional[List[str]], optional): List of file paths to include. Defaults to None.
        """
        super().__init__()
        self.llm = llm
        self.instruction = instruction
        self.output_parser = output_parser or (lambda x: x)
        self.role = role
        self.file_paths = file_paths or []
        
        self._result_event = asyncio.Event()
        self._result = None
        self._agent = None

        # Log file paths if provided
        if self.file_paths:
            logger.info(f"SimpleTask initialized with {len(self.file_paths)} file paths")

    def _on_agent_response(self, *args, **kwargs):
        """
        Handle agent responses and capture the final result.
        
        Registered as an event listener to capture the final response.
        """
        response = kwargs.get('response')
        is_complete = kwargs.get('is_complete', False)
        
        if is_complete and response:
            try:
                self._result = self.output_parser(response)
                self._result_event.set()
                logger.info(f"SimpleTask result captured: {self._result}")
            except Exception as e:
                logger.error(f"Error parsing task result: {e}")
                self._result = None
                self._result_event.set()

    async def execute(self) -> Any:
        """
        Execute the task and retrieve the result.

        Returns:
            The parsed result of the task execution.
        """
        try:
            # Create UserMessage with instruction and file paths
            user_message = UserMessage(
                content=self.instruction, 
                file_paths=self.file_paths
            )

            # Create StandaloneAgent with no tools
            self._agent = StandaloneAgent(
                role=self.role,
                llm=self.llm,
                tools=[],  # No tools for SimpleTask
                use_xml_parser=True,
                initial_user_message=user_message
            )

            # Log file paths details
            if self.file_paths:
                logger.info(f"Executing SimpleTask with {len(self.file_paths)} file paths: {self.file_paths}")

            # Subscribe to agent responses
            self._agent.subscribe(
                EventType.ASSISTANT_RESPONSE, 
                self._on_agent_response, 
                self._agent.agent_id
            )

            # Start the agent
            await self._agent.run()

            # Wait for result
            await self._result_event.wait()

            return self._result

        except Exception as e:
            logger.error(f"Error executing SimpleTask: {e}")
            raise
        finally:
            if self._agent:
                await self._agent.cleanup()

    def get_result(self) -> Optional[Any]:
        """
        Retrieve the task result synchronously.

        Returns:
            The task result if available, None otherwise.
        """
        return self._result