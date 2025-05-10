from dataclasses import dataclass
from typing import List, Optional
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.response_parser.base_response_parser import BaseResponseParser

@dataclass
class AgentInstance:
    """
    Represents the configuration and static data of an agent.
    This class holds the "blueprint" of an agent without containing runtime logic.
    """
    role: str
    agent_id: str
    llm: BaseLLM
    tools: List[BaseTool]
    response_parsers: List[BaseResponseParser]
    
    def __post_init__(self):
        """Initialize tools with agent_id after dataclass construction."""
        if self.tools:
            for tool in self.tools:
                tool.set_agent_id(self.agent_id)
