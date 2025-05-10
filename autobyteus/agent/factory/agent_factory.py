# file: autobyteus/agent/factory/agent_factory.py
import logging
from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.agent_instance import AgentInstance
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.llm.models import LLMModel
from autobyteus.agent.response_parser.base_response_parser import BaseResponseParser
from autobyteus.agent.response_parser.tool_usage_command_parser import ToolUsageCommandParser
from typing import List, Union, Optional

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory class for creating different types of agents.

    This factory simplifies the creation of AgentInstance objects and their
    corresponding runtime agents.
    """
    def __init__(self,
                 role: str,
                 agent_type: str,
                 tool_factory: ToolFactory,
                 llm_factory: LLMFactory,
                 llm_model: LLMModel,
                 tool_names: List[str],
                 response_parsers: Optional[List[BaseResponseParser]] = None):
        """
        Initializes the AgentFactory.

        Args:
            role: The role the created agents will fulfill.
            agent_type: The type of agent to create ("standalone" or "group_aware").
            tool_factory: A factory to create tool instances.
            llm_factory: A factory to create LLM instances.
            llm_model: The specific LLM model configuration to use.
            tool_names: A list of tool names the agent should be equipped with.
            response_parsers: Optional list of response parsers to use.
        """
        self.role = role
        self.agent_type = agent_type
        self.tool_factory = tool_factory
        self.llm_factory = llm_factory
        self.llm_model = llm_model
        self.tool_names = tool_names
        self.response_parsers = response_parsers or []
        logger.info(f"AgentFactory initialized for role '{role}' and type '{agent_type}'")

    def create_agent_instance(self, agent_id: str) -> AgentInstance:
        """
        Creates an AgentInstance with the given configuration.

        Args:
            agent_id: The unique identifier for the agent being created.

        Returns:
            An AgentInstance object with the configured properties.
        """
        logger.info(f"Creating agent instance with id '{agent_id}' for role '{self.role}'")
        
        try:
            tools = [self.tool_factory.create_tool(name) for name in self.tool_names]
            logger.debug(f"Tools created for agent '{agent_id}': {[tool.get_name() for tool in tools]}")
        except Exception as e:
            logger.error(f"Error creating tools for agent '{agent_id}': {e}")
            raise ValueError(f"Failed to create tools for agent {agent_id}: {e}") from e

        try:
            llm = self.llm_factory.create_llm(self.llm_model)
            logger.debug(f"LLM instance created for agent '{agent_id}' using model '{self.llm_model.model_name}'")
        except Exception as e:
            logger.error(f"Error creating LLM for agent '{agent_id}': {e}")
            raise ValueError(f"Failed to create LLM for agent {agent_id}: {e}") from e

        return AgentInstance(
            role=self.role,
            agent_id=agent_id,
            llm=llm,
            tools=tools,
            response_parsers=self.response_parsers
        )

    def create_agent_runtime(self, agent_id: str) -> Union[AgentRuntime, GroupAwareAgent]:
        """
        Creates an agent runtime with the given configuration.

        Args:
            agent_id: The unique identifier for the agent being created.

        Returns:
            An instance of AgentRuntime or GroupAwareAgent.

        Raises:
            ValueError: If the configured agent_type is unsupported.
        """
        agent_instance = self.create_agent_instance(agent_id)
        
        if self.agent_type == "standalone":
            logger.debug(f"Instantiating AgentRuntime for instance: {agent_id}")
            return AgentRuntime(agent_instance)
        elif self.agent_type == "group_aware":
            logger.debug(f"Instantiating GroupAwareAgent runtime for instance: {agent_id}")
            return GroupAwareAgent(agent_instance)
        else:
            logger.error(f"Unsupported agent type specified in factory: {self.agent_type}")
            raise ValueError(f"Unsupported agent type: {self.agent_type}")
