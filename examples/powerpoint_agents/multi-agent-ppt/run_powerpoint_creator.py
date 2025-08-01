import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}")
    else:
        print(f"Info: No .env file found at: {env_file_path}. Relying on exported environment variables.")
except ImportError:
    print("Warning: python-dotenv not installed. Cannot load .env file.")

try:
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.agent.group.agent_group import AgentGroup
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory
    from autobyteus.tools.powerpoint_creator import create_powerpoint
    from autobyteus.tools.image_generator import generate_images
    from autobyteus.tools.image_saver import save_images
    from autobyteus.tools.bash.bash_executor import bash_executor
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger("powerpoint_creator_agent_example")

def setup_logging(args: argparse.Namespace):
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

async def main(args: argparse.Namespace):
    logger.info("--- Starting PowerPoint Creator Agent Example ---")

    llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

    research_agent_config = AgentConfig(
        name="ResearchAgent",
        role="Researcher",
        description="An agent that researches a topic and provides a summary.",
        llm_instance=llm_instance,
        system_prompt="You are a research assistant. Your task is to research the given topic and provide a detailed summary.",
        tools=[bash_executor],
    )

    content_agent_config = AgentConfig(
        name="ContentAgent",
        role="ContentCreator",
        description="An agent that takes a summary and creates content for a PowerPoint presentation.",
        llm_instance=llm_instance,
        system_prompt="You are a content creator. Your task is to take the provided summary and create engaging content for a PowerPoint presentation.",
        tools=[],
    )

    image_agent_config = AgentConfig(
        name="ImageAgent",
        role="ImageCreator",
        description="An agent that generates images for a PowerPoint presentation.",
        llm_instance=llm_instance,
        system_prompt="You are an image creator. Your task is to generate images based on the provided prompts.",
        tools=[generate_images, save_images],
    )

    powerpoint_agent_config = AgentConfig(
        name="PowerPointAgent",
        role="PowerPointCreator",
        description="An agent that creates a PowerPoint presentation from the provided content and images.",
        llm_instance=llm_instance,
        system_prompt="You are a PowerPoint creator. Your task is to create a PowerPoint presentation from the provided content and images.",
        tools=[create_powerpoint],
    )

    agent_group = AgentGroup(
        agent_configs=[
            research_agent_config,
            content_agent_config,
            image_agent_config,
            powerpoint_agent_config,
        ],
        coordinator_config_name="ResearchAgent",
    )

    await agent_group.start()

    initial_input = f"Research the topic '{args.topic}' and create a PowerPoint presentation about it."
    final_response = await agent_group.process_task_for_coordinator(initial_input)

    logger.info(f"Final response from the agent group: {final_response}")

    await agent_group.stop()

    logger.info("--- PowerPoint Creator Agent Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PowerPoint Creator Agent.")
    parser.add_argument("--llm-model", type=str, default="gemini-2.0-flash", help="The LLM model to use.")
    parser.add_argument("--topic", type=str, required=True, help="The topic to create a PowerPoint presentation about.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")

    parsed_args = parser.parse_args()
    setup_logging(parsed_args)

    try:
        asyncio.run(main(parsed_args))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
    finally:
        logger.info("Exiting script.")