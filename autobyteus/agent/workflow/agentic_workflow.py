import logging
import uuid
from typing import List, Dict, Optional, Any, cast

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.group.agent_group import AgentGroup

logger = logging.getLogger(__name__)

class AgenticWorkflow:
    """
    A concrete class for defining and running multi-agent workflows declaratively.
    It internally manages an AgentGroup and provides a user-friendly interface
    to process tasks.
    """
    def __init__(self,
                 agent_factory: AgentFactory,
                 agent_definitions: List[AgentDefinition],
                 coordinator_definition_name: str,
                 workflow_id: Optional[str] = None,
                 agent_runtime_configs: Optional[Dict[str, Dict[str, Any]]] = None,
                 input_param_name: str = "input",
                ):
        """
        Initializes the AgenticWorkflow.

        Args:
            agent_factory: The factory to be used by the internal AgentGroup.
            agent_definitions: List of AgentDefinitions for the agents in this workflow.
            coordinator_definition_name: Name of the agent definition to be used as coordinator.
            workflow_id: Optional. A unique ID for this workflow instance. Auto-generated if None.
            agent_runtime_configs: Optional. Runtime configurations for agents within the group,
                                   passed to AgentGroup. Example:
                                   { "agent_def_name": {
                                        "llm_model_name": "GPT_4O_API", 
                                        "custom_llm_config": LLMConfig(temperature=0.5) or {"temperature": 0.5},
                                        "custom_tool_config": {"ToolName": ToolConfig(...)},
                                        "auto_execute_tools": True/False # UPDATED DOCSTRING KEY
                                     }
                                   }
                                   If "custom_llm_config" is a dict, AgentGroup will convert it to LLMConfig.
                                   The 'llm_model_name' (string) is mandatory in the config if the agent needs an LLM.
            input_param_name: The key to use in `process(**kwargs)` to find the initial
                              input string for the coordinator. Defaults to "input".
        """
        self.workflow_id: str = workflow_id or f"workflow_{uuid.uuid4()}"
        self._input_param_name: str = input_param_name

        logger.info(f"Initializing AgenticWorkflow '{self.workflow_id}'. "
                    f"Input parameter name for process(): '{self._input_param_name}'.")

        self.agent_group: AgentGroup = AgentGroup(
            agent_factory=agent_factory,
            agent_definitions=agent_definitions,
            coordinator_definition_name=coordinator_definition_name,
            group_id=f"group_for_{self.workflow_id}",
            agent_runtime_configs=agent_runtime_configs
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
                f"coordinator='{self.agent_group.coordinator_definition_name}', "
                f"is_running={self.is_running}>")

