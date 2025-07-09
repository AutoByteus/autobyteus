#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.utils.wait_for_idle import wait_for_agent_to_be_idle
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.tools.functional_tool import tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool(name="simple_tool")
async def simple_tool(text: str) -> str:
    """A simple tool that echoes text."""
    return f"Echo: {text}"

async def main():
    """Test basic agent functionality with Gemini"""
    try:
        LLMFactory.reinitialize()
        
        # Simple system prompt without complex instructions
        system_prompt = "You are a helpful assistant. You have access to tools. Use them when appropriate."
        
        agent_llm = LLMFactory.create_llm(
            model_identifier="GEMINI_2_0_FLASH_API",  # Use Flash instead of Pro
            llm_config=LLMConfig(temperature=0.3)
        )

        agent_config = AgentConfig(
            name="SimpleTestAgent",
            role="Test assistant",
            description="A simple test agent",
            llm_instance=agent_llm,
            system_prompt=system_prompt,
            tools=[simple_tool],
            auto_execute_tools=True,
            use_xml_tool_format=False  # Use JSON format instead
        )

        agent_factory = AgentFactory()
        agent = agent_factory.create_agent(config=agent_config)

        # Simple test message
        test_message = "Hello, can you use the simple_tool to echo 'test message'?"
        agent_input = AgentInputUserMessage(content=test_message)

        agent.start()
        
        logger.info("Waiting for agent to be ready...")
        await wait_for_agent_to_be_idle(agent, timeout=30.0)

        await agent.post_user_message(agent_input)
        await asyncio.sleep(1.0)

        logger.info("Waiting for agent to complete...")
        await wait_for_agent_to_be_idle(agent, timeout=60.0)

        logger.info("✅ Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.is_running:
            await agent.stop()

if __name__ == "__main__":
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        sys.exit(1)
        
    asyncio.run(main()) 