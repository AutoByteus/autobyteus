import asyncio
import logging
from typing import Optional, Callable, Any, List, Union

from autobyteus.agent.agent import Agent
from autobyteus.events.event_types import EventType
from autobyteus.llm.models import LLMModel
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.conversation.user_message import UserMessage

logger = logging.getLogger(__name__)

class SimpleTask:
    """
    A simplified task execution class for running single-instruction tasks
    with minimal configuration and built-in result handling.
    """
    
    def __init__(
        self,
        name: str,
        instruction: str,
        llm_model: LLMModel,
        input_data: Optional[Union[str, List[str]]] = None,
        output_parser: Optional[Callable[[str], Any]] = None,
    ):
        """
        Initialize a SimpleTask.

        Args:
            name (str): Name of the task
            instruction (str): Task instruction/prompt
            llm_model (LLMModel): LLM model to use
            input_data (Optional[Union[str, List[str]]], optional): Input data or file paths. Defaults to None.
            output_parser (Optional[Callable], optional): Function to parse the output. Defaults to None.
        """
        self.name = name
        self.instruction = instruction
        self.llm_model = llm_model
        self.input_data = input_data if isinstance(input_data, list) else ([input_data] if input_data else [])
        self.output_parser = output_parser
        
        logger.info(f"Initialized task '{self.name}' with model {self.llm_model.value} and {len(self.input_data)} inputs")

    async def execute(self) -> Any:
        """
        Execute the task and return the result.

        Returns:
            The result of the task execution, parsed if output_parser is provided
        """
        try:
            llm = LLMFactory.create_llm(self.llm_model)
            
            user_message = UserMessage(
                content=self.instruction,
                file_paths=self.input_data
            )

            agent = Agent(
                role=self.name,
                llm=llm,
                initial_user_message=user_message
            )

            result_queue = asyncio.Queue()

            async def handle_response(*args, **kwargs):
                response = kwargs.get('response')
                if response:
                    await result_queue.put(response)

            agent.subscribe(EventType.ASSISTANT_RESPONSE, handle_response, agent.agent_id)

            try:
                agent.start()
                result = await asyncio.wait_for(
                    result_queue.get(),
                    timeout=30.0
                )
                
                # Only parse if output_parser is provided
                if self.output_parser:
                    return self.output_parser(result)
                return result

            except asyncio.TimeoutError:
                logger.error(f"Task '{self.name}' timed out")
                raise TimeoutError(f"Task '{self.name}' execution timed out")

            finally:
                agent.unsubscribe("ASSISTANT_RESPONSE", handle_response, agent.agent_id)
                agent.stop()
                await agent.cleanup()

        except Exception as e:
            logger.error(f"Error executing task '{self.name}': {str(e)}")
            raise