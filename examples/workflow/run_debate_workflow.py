# file: autobyteus/examples/workflow/run_debate_workflow.py
"""
This example script demonstrates a hierarchical workflow.
A parent workflow (The Debate) manages two sub-workflows (Debating Teams)
and a regular agent (The Analyst).
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
    from autobyteus.workflow.context.workflow_config import WorkflowConfig
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "debate_workflow_tui_app.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

def create_debate_workflow(model_name: str):
    """Creates a hierarchical 4-agent debate workflow for the TUI demonstration."""
    # Validate model
    try:
        _ = LLMModel[model_name]
    except KeyError:
        logging.critical(f"LLM Model '{model_name}' is not valid. Use --help-models to see available models.")
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid. Use --help-models to see available models.\nCheck log file for details.")
        sys.exit(1)

    # --- AGENT CONFIGURATIONS ---

    # Parent-Level Agents
    moderator_config = AgentConfig(
        name="DebateModerator", role="Coordinator", description="Manages the debate, gives turns, and summarizes.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are the impartial moderator of a debate between two teams. Your goal is to facilitate a structured debate on a user's topic.\n"
            "Your team consists of Team_Affirmative, Team_Negative, and an Analyst. You will delegate tasks to them using their unique names.\n"
            "Responsibilities: 1. Announce the topic. 2. Ask Team_Affirmative for an opening statement. 3. Ask Team_Negative for a rebuttal. "
            "4. Facilitate a structured flow of arguments. 5. Call upon the Analyst for summaries. 6. Conclude the debate.\n"
            "You MUST use the `SendMessageTo` tool to communicate with your team. Do not debate yourself.\n\n{{tools}}"
        )
    )
    analyst_config = AgentConfig(
        name="Analyst", role="Specialist", description="Provides neutral analysis of the debate.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are a neutral Analyst in a debate. You will receive instructions from the DebateModerator. Your role is to provide objective analysis, summarize points, and identify logical fallacies. Remain neutral.\n\n{{tools}}"
        )
    )

    # Team Affirmative Agents
    lead_affirmative_config = AgentConfig(
        name="Lead_Affirmative", role="Coordinator", description="Leads the team arguing FOR the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are the lead of the Affirmative team. You receive high-level instructions from the DebateModerator (e.g., 'prepare opening statement').\n"
            "Your job is to delegate this task to your team member, the Proponent, by giving them a specific instruction.\n\n{{tools}}"
        )
    )
    proponent_config = AgentConfig(
        name="Proponent", role="Debater", description="Argues in favor of the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are a Proponent. You will receive instructions from your team lead. Your role is to argue STRONGLY and PERSUASIVELY IN FAVOR of the motion."
    )

    # Team Negative Agents
    lead_negative_config = AgentConfig(
        name="Lead_Negative", role="Coordinator", description="Leads the team arguing AGAINST the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are the lead of the Negative team. You receive high-level instructions from the DebateModerator (e.g., 'prepare your rebuttal').\n"
            "Your job is to delegate this task to your team member, the Opponent, by giving them a specific instruction.\n\n{{tools}}"
        )
    )
    opponent_config = AgentConfig(
        name="Opponent", role="Debater", description="Argues against the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are an Opponent. You will receive instructions from your team lead. Your role is to argue STRONGLY and PERSUASIVELY AGAINST the motion."
    )

    # --- BUILD SUB-WORKFLOWS ---
    
    # Build Team Affirmative
    team_affirmative_workflow: WorkflowConfig = (
        WorkflowBuilder(name="Team_Affirmative", description="A two-agent team that argues in favor of a proposition.", role="Argues FOR the motion")
        .set_coordinator(lead_affirmative_config)
        .add_agent_node(proponent_config)
        .build()._runtime.context.config # Build to get the config object
    )
    
    # Build Team Negative
    team_negative_workflow: WorkflowConfig = (
        WorkflowBuilder(name="Team_Negative", description="A two-agent team that argues against a proposition.", role="Argues AGAINST the motion")
        .set_coordinator(lead_negative_config)
        .add_agent_node(opponent_config)
        .build()._runtime.context.config # Build to get the config object
    )

    # --- BUILD PARENT WORKFLOW ---
    
    debate_workflow = (
        WorkflowBuilder(name="Grand_Debate", description="A hierarchical workflow for a moderated debate between two teams.")
        .set_coordinator(moderator_config)
        .add_workflow_node(team_affirmative_workflow)
        .add_workflow_node(team_negative_workflow)
        .add_agent_node(analyst_config)
        .build()
    )

    return debate_workflow

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the workflow and run the TUI app."""
    print("Setting up hierarchical debate workflow...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    try:
        workflow = create_debate_workflow(model_name=args.llm_model)
        app = WorkflowApp(workflow=workflow)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run debate workflow TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a hierarchical 2-team debate workflow with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help="The LLM model to use for the agents.")
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
