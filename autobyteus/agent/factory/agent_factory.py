# file: autobyteus/agent/factory/agent_factory.py
from autobyteus.agent.agent import StandaloneAgent
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.llm.rpa.factory.rpa_llm_factory import RPALLMFactory
from autobyteus.prompt.prompt_builder import PromptBuilder
from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.llm.models import LLMModel
from typing import Type, List, Optional

class AgentFactory:
    def __init__(self, 
                 role: str,
                 agent_type: str,
                 tool_factory: ToolFactory,
                 llm_factory: RPALLMFactory,
                 prompt_builder: PromptBuilder,
                 llm_model: LLMModel,
                 tool_names: List[str],
                 use_xml_parser: bool = True,
                 persistence_provider_class: Optional[Type[PersistenceProvider]] = None):
        self.role = role
        self.agent_type = agent_type
        self.tool_factory = tool_factory
        self.llm_factory = llm_factory
        self.prompt_builder = prompt_builder
        self.llm_model = llm_model
        self.tool_names = tool_names
        self.use_xml_parser = use_xml_parser
        self.persistence_provider_class = persistence_provider_class

    def create_agent(self, agent_id: str) -> StandaloneAgent:
        tools = [self.tool_factory.create_tool(name) for name in self.tool_names]
        llm = self.llm_factory.create_llm(self.llm_model)

        if self.agent_type == "standalone":
            return StandaloneAgent(
                agent_id=agent_id,
                role=self.role,
                prompt_builder=self.prompt_builder,
                llm=llm,
                tools=tools,
                use_xml_parser=self.use_xml_parser,
                persistence_provider_class=self.persistence_provider_class
            )
        elif self.agent_type == "group_aware":
            return GroupAwareAgent(
                agent_id=agent_id,
                role=self.role,
                prompt_builder=self.prompt_builder,
                llm=llm,
                tools=tools,
                use_xml_parser=self.use_xml_parser,
                persistence_provider_class=self.persistence_provider_class
            )
        else:
            raise ValueError(f"Unsupported agent type: {self.agent_type}")