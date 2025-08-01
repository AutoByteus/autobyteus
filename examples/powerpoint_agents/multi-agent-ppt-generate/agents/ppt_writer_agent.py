from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.llm_factory import LLMFactory
from .prompts import PPT_WRITER_PROMPT

def get_ppt_writer_agent_config(tools: list) -> AgentConfig:
    llm_instance = LLMFactory.create_llm("gemini-2.5-pro")
    return AgentConfig(
        name="PPTWriterAgent",
        role="writer",
        description="A specialized agent that takes an outline and writes the full JSON content for a presentation.",
        llm_instance=llm_instance,
        system_prompt=PPT_WRITER_PROMPT,
        tools=tools,
        auto_execute_tools=True,
        use_xml_tool_format=False
    )