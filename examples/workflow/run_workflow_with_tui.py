# file: autobyteus/examples/workflow/run_workflow_with_tui.py
"""
This example script demonstrates how to run an AgenticWorkflow with the
new Textual-based user interface.
"""
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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(PACKAGE_ROOT / ".env")
except ImportError:
    pass

# --- Imports for the Workflow TUI Example ---
try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.workflow.workflow_builder import WorkflowBuilder
    from autobyteus.cli.workflow_tui.app import WorkflowApp
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
# It's crucial to log to a file so that stdout/stderr are free for Textual.
def setup_file_logging() -> Path:
    """
    Sets up file-based logging and returns the path to the log file.
    """
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "workflow_tui_app.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=log_file_path,
        filemode="w",
    )
    # Silence the noisy asyncio logger in the file log
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    
    return log_file_path

def create_demo_workflow(model_name: str):
    """Creates a simple two-agent workflow for the TUI demonstration."""
    # The factory will handle API key checks based on the selected model's provider.

    # Validate model
    try:
        _ = LLMModel[model_name]
    except KeyError:
        logging.critical(f"LLM Model '{model_name}' is not valid. Use --help-models to see available models.")
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid. Use --help-models to see available models.\nCheck log file for details.")
        sys.exit(1)

    # Coordinator Agent Config - Gets its own LLM instance
    coordinator_config = AgentConfig(
        name="Coordinator",
        role="Project Manager",
        description="Delegates tasks to the team to fulfill the user's request.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
    )

    # Specialist Agent Config (FactChecker) - Gets its own LLM instance
    fact_checker_config = AgentConfig(
        name="FactChecker",
        role="Specialist",
        description="An agent with a limited, internal knowledge base for answering direct factual questions.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are a fact-checking bot. You have the following knowledge:\n"
            "- The capital of France is Paris.\n"
            "- The tallest mountain on Earth is Mount Everest.\n"
            "If asked something you don't know, say 'I do not have information on that topic.'"
        )
    )

    # Build the workflow
    workflow = (
        WorkflowBuilder(description="A simple two-agent workflow for demonstrating the TUI.")
        .set_coordinator(coordinator_config)
        .add_node(fact_checker_config, dependencies=[])
        .build()
    )
    return workflow

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the workflow and run the TUI app."""
    print("Setting up workflow...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    try:
        workflow = create_demo_workflow(model_name=args.llm_model)
        app = WorkflowApp(workflow=workflow)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run workflow TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an AgenticWorkflow with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="hf.co/Menlo/Jan-nano-gguf:Q8_0", help="The LLM model to use for the agents.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    
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

    log_file_path = setup_file_logging()
    try:
        asyncio.run(main(parsed_args, log_file_path))
    except KeyboardInterrupt:
        print("\nExiting application.")
    except Exception as e:
        # This catches errors during asyncio.run, which might not be logged otherwise
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck log file for details: {log_file_path.resolve()}")
