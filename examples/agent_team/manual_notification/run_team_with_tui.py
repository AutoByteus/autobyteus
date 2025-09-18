# file: autobyteus/examples/agent_team/manual_notification/run_team_with_tui.py
"""
This example script demonstrates how to run an AgentTeam with the
new Textual-based user interface.
"""
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent.parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(PACKAGE_ROOT / ".env")
except ImportError:
    pass

# --- Imports for the Agent Team TUI Example ---
try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
    from autobyteus.cli.agent_team_tui.app import AgentTeamApp
    from autobyteus.task_management.tools import (
        PublishTasks,
        GetTaskBoardStatus,
        UpdateTaskStatus,
    )
    from autobyteus.agent.message import SendMessageTo
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
    log_file_path = log_dir / "agent_team_tui_app.log"
    
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

def create_demo_team(model_name: str):
    """Creates a simple two-agent team for the TUI demonstration."""
    # The factory will handle API key checks based on the selected model's provider.

    # Validate model
    try:
        _ = LLMModel[model_name]
    except (KeyError, ValueError):
        logging.critical(f"LLM Model '{model_name}' is not valid or is ambiguous.")
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid. Use --help-models to see available unique identifiers.", file=sys.stderr)
        sys.exit(1)

    # Coordinator Agent Config - Gets its own LLM instance
    coordinator_config = AgentConfig(
        name="ProjectManager",
        role="Coordinator",
        description="Delegates tasks to the team to fulfill the user's request.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are an AI agent. Your name is 'ProjectManager'. Your role is to take a user request, create a plan, and manage its execution by your team.\n\n"
            "### Your Team\n"
            "Here is your team member:\n"
            "{{team}}\n\n"
            "### Your Mission Workflow\n"
            "1.  **Analyze and Plan**: Decompose the user's request into a single task for your 'FactChecker' agent.\n"
            "2.  **Publish the Plan**: You MUST use the `PublishTasks` tool to submit your list of tasks to the team's shared task board. This is a critical first step.\n"
            "3.  **Delegate and Inform**: Use the `SendMessageTo` tool to notify your 'FactChecker' agent that they have a new task.\n"
            "4.  **Wait for Completion**: Await a message from 'FactChecker' that they have completed the task. DO NOT ask for status updates.\n"
            "5.  **Report to User**: Once you receive the completion message, you can use `GetTaskBoardStatus` to review the results and then report them back to the user.\n\n"
            "### CRITICAL RULES\n"
            "- You MUST use the agent's unique, case-sensitive `name` ('FactChecker') when using tools.\n\n"
            "### Your Tools\n"
            "{{tools}}"
        ),
        tools=[PublishTasks(), GetTaskBoardStatus(), SendMessageTo()],
    )

    # Specialist Agent Config (FactChecker) - Gets its own LLM instance
    fact_checker_config = AgentConfig(
        name="FactChecker",
        role="Specialist",
        description="An agent with a limited, internal knowledge base for answering direct factual questions.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are an AI agent. Your name is 'FactChecker'. You are a fact-checking specialist.\n"
            "You will be notified by 'ProjectManager' when a task is ready for you. When you receive a message, you must first use `GetTaskBoardStatus` to find the task assigned to you.\n\n"
            "### Your Knowledge Base\n"
            "- The capital of France is Paris.\n"
            "- The tallest mountain on Earth is Mount Everest.\n\n"
            "### Rules\n"
            "- If asked something you don't know, you MUST respond with: 'I do not have information on that topic.'\n"
            "- After answering, you MUST use the `UpdateTaskStatus` tool to mark your task as 'completed'.\n"
            "- Finally, you MUST use `SendMessageTo` to notify 'ProjectManager' that you are finished.\n\n"
            "Here is the manifest of tools available to you:\n"
            "{{tools}}"
        ),
        tools=[UpdateTaskStatus(), GetTaskBoardStatus(), SendMessageTo()],
    )

    # Build the agent team
    team = (
        AgentTeamBuilder(
            name="TUIDemoTeam",
            description="A simple two-agent team for demonstrating the TUI."
        )
        .set_coordinator(coordinator_config)
        .add_agent_node(fact_checker_config, dependencies=[])
        .build()
    )
    return team

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the agent team and run the TUI app."""
    print("Setting up agent team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    try:
        team = create_demo_team(model_name=args.llm_model)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an AgentTeam with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model identifier to use for the agents.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    
    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized()
            print("Available LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Display Name: {model.name:<30} Identifier: {model.model_identifier}")
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
