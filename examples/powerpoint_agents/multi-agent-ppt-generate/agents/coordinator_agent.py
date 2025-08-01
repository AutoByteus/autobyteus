from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.tools.mcp.tool import GenericMcpTool
from autobyteus.agent.message.send_message_to import SendMessageTo
from .prompts import COORDINATOR_PROMPT

def get_coordinator_agent_config(tools: list) -> AgentConfig:
    llm_instance = LLMFactory.create_llm("gpt-4o")
    
    # Add the essential SendMessageTo tool for inter-agent communication
    all_tools = tools + [SendMessageTo()]
    
    return AgentConfig(
        name="CoordinatorAgent",
        role="coordinator",
        description="The master agent that orchestrates the presentation creation workflow.",
        llm_instance=llm_instance,
        system_prompt=COORDINATOR_PROMPT,
        tools=all_tools,
        auto_execute_tools=True,
        use_xml_tool_format=False
    )