from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.llm_factory import LLMFactory
from .prompts import OUTLINE_PROMPT

def get_outline_agent_config(tools: list) -> AgentConfig:
    llm_instance = LLMFactory.create_llm("claude-4-sonnet")
    return AgentConfig(
        name="OutlineAgent",
        role="outliner",
        description="A specialized agent for creating presentation outlines from a topic.",
        llm_instance=llm_instance,
        system_prompt=OUTLINE_PROMPT,
        tools=tools,
        auto_execute_tools=True,
        use_xml_tool_format=False
    )