# file: autobyteus/examples/workflow/run_basic_research_workflow.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file in the project root
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

# --- Imports for the Workflow Example ---
try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.workflow import AgenticWorkflow
    from autobyteus.agent.workflow.workflow_config import WorkflowConfig
    from autobyteus.agent.workflow.workflow_node_config import WorkflowNodeConfig
    from autobyteus.cli import workflow_cli
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("basic_workflow_example")

def setup_logging(args: argparse.Namespace):
    """Configures logging for the interactive session."""
    loggers_to_clear = [
        logging.getLogger(),
        logging.getLogger("autobyteus"),
        logging.getLogger("autobyteus.cli"),
    ]
    for l in loggers_to_clear:
        if l.hasHandlers():
            for handler in l.handlers[:]:
                l.removeHandler(handler)
                if hasattr(handler, 'close'): handler.close()

    script_log_level = logging.DEBUG if args.debug else logging.INFO

    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    formatted_console_handler = logging.StreamHandler(sys.stdout)
    formatted_console_handler.setFormatter(console_formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(formatted_console_handler)
    root_logger.setLevel(script_log_level) 
    
    # Configure the main log file
    log_file_path = Path(args.log_file).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    agent_file_handler = logging.FileHandler(log_file_path, mode='w')  
    agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
    agent_file_handler.setFormatter(agent_file_formatter)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    autobyteus_logger = logging.getLogger("autobyteus")
    autobyteus_logger.addHandler(agent_file_handler)
    autobyteus_logger.setLevel(file_log_level)
    autobyteus_logger.propagate = True
    
    logger.info(f"Core library logs redirected to: {log_file_path} (level: {logging.getLevelName(file_log_level)})")


async def main(args: argparse.Namespace):
    """Main function to configure and run the research workflow."""
    logger.info("--- Starting Basic Research Workflow Example ---")

    # 1. Create LLM instance for the agents
    try:
        _ = LLMModel[args.llm_model]
    except KeyError:
        logger.error(f"LLM Model '{args.llm_model}' is not valid. Use --help-models to see available models.")
        sys.exit(1)

    logger.info(f"Creating LLM instance for model: {args.llm_model}")
    llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

    # 2. Define the Agent Configurations
    
    # The Coordinator/Manager Agent
    research_manager_config = AgentConfig(
        name="ResearchManager",
        role="Coordinator",
        description="A manager agent that receives research goals and delegates them to specialists.",
        llm_instance=llm_instance,
        system_prompt=(
            "You are the manager of a research team. Your job is to understand the user's research goal and delegate it to the correct specialist agent on your team. "
            "Do not answer questions yourself; always delegate. "
            "You have one specialist available: 'FactChecker'."
            # The --- WORKFLOW CONTEXT --- block will be dynamically appended by the workflow engine.
        ),
        # Tools will be auto-injected by the workflow, including SendMessageTo
    )

    # The Worker/Specialist Agent
    fact_checker_config = AgentConfig(
        name="FactChecker",
        role="Specialist",
        description="An agent with a limited, internal knowledge base for answering direct factual questions.",
        llm_instance=llm_instance,
        system_prompt=(
            "You are a fact-checking bot. You have the following knowledge:\n"
            "- The capital of France is Paris.\n"
            "- The tallest mountain on Earth is Mount Everest.\n"
            "- The primary programming language for AutoByteUs is Python.\n"
            "You MUST ONLY answer questions based on this knowledge. If you are asked something you do not know, you MUST respond with 'I do not have information on that topic.'"
        )
    )

    # 3. Define the Workflow Structure
    
    # Create nodes for the workflow graph
    manager_node = WorkflowNodeConfig(agent_config=research_manager_config)
    checker_node = WorkflowNodeConfig(agent_config=fact_checker_config)
    
    # Assemble the final workflow configuration
    workflow_config = WorkflowConfig(
        nodes=[manager_node, checker_node],
        coordinator_node=manager_node,
        description="A simple two-agent workflow for delegating and answering research questions."
    )
    
    # 4. Create and Run the Workflow
    
    research_workflow = AgenticWorkflow(config=workflow_config)
    logger.info(f"Workflow instance created with ID: {research_workflow.workflow_id}")

    try:
        logger.info("Starting interactive workflow session...")
        await workflow_cli.run_workflow(
            workflow=research_workflow, 
            initial_prompt=args.initial_prompt
        )
        logger.info("Interactive workflow session finished.")
    except Exception as e:
        logger.error(f"An error occurred during the workflow execution: {e}", exc_info=True)
    
    logger.info("--- Basic Research Workflow Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a basic two-agent research workflow.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help="The LLM model to use for the agents.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--initial-prompt", type=str, help="An optional initial prompt to start the workflow automatically.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--log-file", type=str, default="./workflow_logs.txt", 
                       help="Path to the log file for autobyteus library logs.")

    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized() 
            print("Available LLM Models (you can use either name or value with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.name)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Name: {model.name:<35} Value: {model.value}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)

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

