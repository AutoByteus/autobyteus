# file: autobyteus/examples/run_agent_with_skill.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
except ImportError:
    pass

# --- Imports ---
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.models import LLMModel
from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.cli import agent_cli
from autobyteus.tools.registry import default_tool_registry

logger = logging.getLogger("agent_skill_example")
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

def setup_logging(args: argparse.Namespace):
    """
    Configures logging for the interactive session.
    """
    loggers_to_clear = [
        logging.getLogger(),
        logging.getLogger("autobyteus"),
        logging.getLogger("autobyteus.cli"),
        interactive_logger,
    ]
    for l in loggers_to_clear:
        if l.hasHandlers():
            for handler in l.handlers[:]:
                l.removeHandler(handler)
                if hasattr(handler, 'close'):
                    handler.close()

    script_log_level = logging.DEBUG if args.debug else logging.INFO

    # 1. Handler for unformatted interactive output
    interactive_handler = logging.StreamHandler(sys.stdout)
    interactive_logger.addHandler(interactive_handler)
    interactive_logger.setLevel(logging.INFO)
    interactive_logger.propagate = False

    # 2. Handler for formatted console logs
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    class FormattedConsoleFilter(logging.Filter):
        def filter(self, record):
            if record.name.startswith("agent_skill_example") or record.name.startswith("autobyteus.cli"):
                return True
            if record.levelno >= logging.CRITICAL:
                return True
            return False

    formatted_console_handler = logging.StreamHandler(sys.stdout)
    formatted_console_handler.setFormatter(console_formatter)
    formatted_console_handler.addFilter(FormattedConsoleFilter())

    root_logger = logging.getLogger()
    root_logger.addHandler(formatted_console_handler)
    root_logger.setLevel(script_log_level)

    # 3. Handler for the main agent log file
    log_file_path = Path(args.agent_log_file).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')
    agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    agent_file_handler.setFormatter(agent_file_formatter)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True

    # 4. Isolate noisy queue manager logs to a separate file in debug mode
    if args.debug:
        queue_log_file_path = Path(log_file_path.parent / f"{log_file_path.stem}_queue.log").resolve()

        queue_file_handler = logging.FileHandler(queue_log_file_path, mode='w')
        queue_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        queue_file_handler.setFormatter(queue_file_formatter)

        queue_logger = logging.getLogger("autobyteus.agent.events.agent_input_event_queue_manager")

        queue_logger.setLevel(logging.DEBUG)
        queue_logger.addHandler(queue_file_handler)
        queue_logger.propagate = False

        logger.info(f"Debug mode: Redirecting noisy queue manager DEBUG logs to: {queue_log_file_path}")

    # 5. Configure `autobyteus.cli` package logging
    cli_logger = logging.getLogger("autobyteus.cli")
    cli_logger.setLevel(script_log_level)
    cli_logger.propagate = True

    logger.info(f"Core library logs (excluding CLI) redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")

async def main(args: argparse.Namespace):
    logger.info("--- Starting Agent Skills Example ---")

    # 1. Define the path to our example skill
    skill_path = str(PACKAGE_ROOT / "examples" / "skills" / "image_concatenator")
    
    if not Path(skill_path).exists():
        logger.error(f"Skill directory not found at: {skill_path}")
        sys.exit(1)

    try:
        # 2. Create LLM
        logger.info(f"Creating LLM instance for model: {args.llm_model}")
        llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

        # 3. Create Tools
        # We need 'run_bash' to execute the skill's script
        # We need 'read_file' if the agent wants to inspect the script (optional but good practice)
        tools = [
            default_tool_registry.create_tool("run_bash"), 
            default_tool_registry.create_tool("read_file")
        ]

        # 4. Configure Agent with Preloaded Skill
        config = AgentConfig(
            name="ImageOpsAgent",
            role="Operator",
            description="An agent capable of image operations using local skills.",
            llm_instance=llm_instance,
            system_prompt="You are a helpful assistant. Use your skills to answer user requests.",
            tools=tools,
            skills=[skill_path], # <--- Preloading the skill via path
            auto_execute_tools=False # Let user see the command before execution
        )

        agent = AgentFactory().create_agent(config=config)
        logger.info(f"Agent created with preloaded skill: {skill_path}")

        # 5. Run Interactive Session
        print(f"\nSkill loaded from: {skill_path}")
        print("Try asking: 'Please concatenate img1.png and img2.png into merged.png'")
        await agent_cli.run(agent=agent)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an agent with a preloaded skill.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help="LLM model identifier.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_skill.txt",
                        help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs_skill.txt)")

    args = parser.parse_args()
    setup_logging(args)

    try:
        asyncio.run(main(args))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
