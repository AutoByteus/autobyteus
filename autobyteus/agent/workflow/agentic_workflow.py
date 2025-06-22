# file: autobyteus/autobyteus/agent/workflow/agentic_workflow.py
import logging
import uuid
from typing import List, Dict, Optional, Any, cast

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.group.agent_group import AgentGroup

logger = logging.getLogger(__name__)

class AgenticWorkflow:
    """
    A concrete class for defining and running multi-agent workflows declaratively.
    It internally manages an AgentGroup and provides a user-friendly interface
    to process tasks.
    """
    def __init__(self,
                 agent_configs: List[AgentConfig],
                 coordinator_config_name: str,
                 workflow_id: Optional[str] = None,
                 input_param_name: str = "input",
                ):
        """
        Initializes the AgenticWorkflow.

        Args:
            agent_configs: List of pre-made AgentConfig instances for the agents in this workflow.
            coordinator_config_name: Name of the agent config to be used as coordinator.
            workflow_id: Optional. A unique ID for this workflow instance. Auto-generated if None.
            input_param_name: The key to use in `process(**kwargs)` to find the initial
                              input string for the coordinator. Defaults to "input".
        """
        self.workflow_id: str = workflow_id or f"workflow_{uuid.uuid4()}"
        self._input_param_name: str = input_param_name

        logger.info(f"Initializing AgenticWorkflow '{self.workflow_id}'. "
                    f"Input parameter name for process(): '{self._input_param_name}'.")

        # The AgentGroup is now initialized directly with the user-provided configs.
        self.agent_group: AgentGroup = AgentGroup(
            agent_configs=agent_configs,
            coordinator_config_name=coordinator_config_name,
            group_id=f"group_for_{self.workflow_id}",
        )
        logger.info(f"AgenticWorkflow '{self.workflow_id}' successfully instantiated internal AgentGroup '{self.agent_group.group_id}'.")

    async def process(self, **kwargs: Any) -> Any:
        logger.info(f"AgenticWorkflow '{self.workflow_id}' received process request with kwargs: {list(kwargs.keys())}")

        initial_input_content = kwargs.get(self._input_param_name)
        if initial_input_content is None:
            raise ValueError(f"Required input parameter '{self._input_param_name}' not found in process() arguments.")
        if not isinstance(initial_input_content, str):
            raise ValueError(f"Input parameter '{self._input_param_name}' must be a string, "
                             f"got {type(initial_input_content).__name__}.")

        user_id: Optional[str] = cast(Optional[str], kwargs.get("user_id")) if isinstance(kwargs.get("user_id"), str) else None
        
        logger.debug(f"AgenticWorkflow '{self.workflow_id}': Extracted initial input for coordinator: '{initial_input_content[:100]}...'")

        result = await self.agent_group.process_task_for_coordinator(
            initial_input_content=initial_input_content,
            user_id=user_id
        )
        
        return result


    async def start(self) -> None:
        logger.info(f"AgenticWorkflow '{self.workflow_id}' received start() request. Delegating to AgentGroup.")
        await self.agent_group.start()

    async def stop(self, timeout: float = 10.0) -> None:
        logger.info(f"AgenticWorkflow '{self.workflow_id}' received stop() request. Delegating to AgentGroup.")
        await self.agent_group.stop(timeout)

    @property
    def is_running(self) -> bool:
        return self.agent_group.is_running

    @property
    def group_id(self) -> str:
        return self.agent_group.group_id

    def __repr__(self) -> str:
        return (f"<AgenticWorkflow workflow_id='{self.workflow_id}', "
                f"group_id='{self.agent_group.group_id}', "
                f"coordinator='{self.agent_group.coordinator_config_name}', "
                f"is_running={self.is_running}>")
