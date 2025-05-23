import pytest
import asyncio
from pathlib import Path
import logging # Using logging for test output

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.llm.models import LLMModel
from autobyteus.agent.registry.agent_registry import default_agent_registry
from autobyteus.agent.agent import Agent
from autobyteus.agent.status import AgentStatus

# Configure basic logging for the test module if you want to see autobyteus logs
# This is a simple setup; a real project might have a more sophisticated logging config for tests.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_poem_writer_agent_integration(tmp_path: Path):
    """
    Integration test for PoemWriterAgent.
    Tests the end-to-end flow:
    1. Agent receives a topic.
    2. Agent uses LLM (GPT-4o) to generate a poem.
    3. Agent uses WriteFileTool to save the poem to a file.
    4. Test verifies the file creation and content in a temporary directory.
    """
    logger.info(f"Starting test_poem_writer_agent_integration. Temporary path: {tmp_path}")

    # 1. Define AgentDefinition for the PoemWriterAgent
    poem_file_name = "poem.txt"
    # It's crucial that the LLM is instructed to use this exact path.
    # Ensure the path format is suitable for the LLM (e.g., POSIX style).
    poem_output_path = (tmp_path / poem_file_name).resolve() # Use absolute path

    system_prompt = (
        f"You are an excellent poet. When given a topic, you must write a creative poem. "
        f"After writing the poem, you MUST use the 'WriteFileTool' to save your complete poem. "
        f"The 'WriteFileTool' requires two arguments: 'file_path' and 'content'. "
        f"You MUST save the poem to the following absolute file path: '{poem_output_path.as_posix()}'. "
        f"Do not ask for confirmation before using the tool. Execute the tool call directly."
    )

    # Using a unique name for the test agent definition to avoid conflicts
    # The AgentDefinition metaclass will auto-register this definition.
    poem_writer_def = AgentDefinition(
        name="TestPoemWriterAgent_Integration", 
        role="CreativePoetIntegrationTest",
        description="An agent that writes poems on specified topics and saves them to disk for integration testing.",
        system_prompt=system_prompt,
        tool_names=["WriteFileTool"]  # Assumes 'WriteFileTool' is registered in default_tool_registry
    )
    logger.info(f"AgentDefinition created: {poem_writer_def.name}")

    # 2. Instantiate the PoemWriterAgent using AgentFactory (via default_agent_registry)
    # This relies on default_agent_registry being properly configured with an LLMFactory
    # that can handle GPT_4O_API and a ToolRegistry that includes WriteFileTool.
    agent: Agent = default_agent_registry.create_agent(
        definition=poem_writer_def,
        llm_model=LLMModel.GPT_4O_API, # Specify the LLM model
        auto_execute_tools=True, # Explicitly set as per requirement
        # No specific workspace is passed; WriteFileTool will use the absolute path from the prompt.
    )
    logger.info(f"Agent instance created: {agent.agent_id}")

    try:
        # 3. Start the agent
        agent.start()
        logger.info(f"Agent {agent.agent_id} starting...")

        # Wait for the agent to become IDLE after starting
        start_timeout_seconds = 20
        poll_interval_seconds = 0.2
        elapsed_time_seconds = 0
        
        logger.info(f"Waiting for agent {agent.agent_id} to become IDLE...")
        while agent.get_status() != AgentStatus.IDLE and elapsed_time_seconds < start_timeout_seconds:
            await asyncio.sleep(poll_interval_seconds)
            elapsed_time_seconds += poll_interval_seconds
            logger.debug(f"Agent {agent.agent_id} status: {agent.get_status()}. Time elapsed: {elapsed_time_seconds:.1f}s")

        if agent.get_status() != AgentStatus.IDLE:
            pytest.fail(
                f"Agent {agent.agent_id} did not become IDLE within {start_timeout_seconds}s. "
                f"Current status: {agent.get_status()}"
            )
        logger.info(f"Agent {agent.agent_id} is IDLE.")

        # 4. Send an AgentInputUserMessage to the agent
        user_message_content = "Write a short poem about a peaceful lake at dawn."
        input_message = AgentInputUserMessage(content=user_message_content)
        
        logger.info(f"Sending message to agent {agent.agent_id}: '{user_message_content}'")
        await agent.post_user_message(input_message)

        # 5. Wait for the agent to process the message and for the WriteFileTool to create the file
        # Polling mechanism to check for file creation and content
        file_check_timeout_seconds = 120  # Increased timeout for LLM + tool execution
        elapsed_time_seconds = 0
        file_created_and_has_content = False
        
        logger.info(f"Waiting for poem file '{poem_output_path}' to be created with content...")
        while elapsed_time_seconds < file_check_timeout_seconds:
            if poem_output_path.exists() and poem_output_path.stat().st_size > 0:
                file_created_and_has_content = True
                logger.info(f"File '{poem_output_path}' found with content.")
                break
            await asyncio.sleep(poll_interval_seconds)
            elapsed_time_seconds += poll_interval_seconds
            logger.debug(f"Polling for file '{poem_output_path}'. Time elapsed: {elapsed_time_seconds:.1f}s")
        
        # 6. Assertions
        assert file_created_and_has_content, \
            f"Poem file '{poem_output_path}' was not created or is empty after {file_check_timeout_seconds}s."

        poem_content = poem_output_path.read_text(encoding='utf-8')
        assert len(poem_content.strip()) > 0, "Poem file content is empty or contains only whitespace."
        
        logger.info(f"Successfully verified poem file creation and content. Poem:\n{poem_content[:300]}...")

    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
        raise # Re-raise the exception to fail the test
    finally:
        # 7. Stop the agent to clean up resources (e.g., background tasks)
        logger.info(f"Stopping agent {agent.agent_id}...")
        if agent and agent.is_running:
            await agent.stop(timeout=20) # Generous timeout for shutdown
            logger.info(f"Agent {agent.agent_id} stopped.")
        else:
            logger.info(f"Agent {agent.agent_id} was not running or already stopped.")
        
        # tmp_path directory and its contents are cleaned up automatically by pytest.
    logger.info(f"test_poem_writer_agent_integration completed for agent {agent.agent_id}.")

