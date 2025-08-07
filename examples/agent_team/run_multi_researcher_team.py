# file: autobyteus/examples/agent_team/run_multi_researcher_team.py
"""
This example script demonstrates how the AgentTeam framework handles multiple
agents with the same simple name by creating unique prompt aliases.
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

# --- Imports for the Agent Team TUI Example ---
try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
    from autobyteus.cli.agent_team_tui.app import AgentTeamApp
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "multi_researcher_team_tui_app.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

def create_multi_researcher_team(model_name: str):
    """Creates a three-agent team with two agents sharing the same name."""
    # Validate model
    try:
        _ = LLMModel[model_name]
    except (KeyError, ValueError):
        logging.critical(f"LLM Model '{model_name}' is not valid or is ambiguous.")
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid. Use --help-models to see available unique identifiers.", file=sys.stderr)
        sys.exit(1)

    # --- AGENT CONFIGURATIONS ---
    
    # Coordinator Agent
    coordinator_config = AgentConfig(
        name="ResearchLead",
        role="Coordinator",
        description="Delegates research tasks to the correct specialist.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt=(
            "You are a research lead. Your team has two specialists, both named Researcher. "
            "One specializes in web research, and the other in database research. "
            "Your job is to delegate user requests to the correct researcher based on the task.\n\n"
            "The system will provide you with a team manifest with unique aliases for each researcher. "
            "You MUST use these unique aliases when using the `SendMessageTo` tool.\n\n"
            "{{tools}}"
        )
    )

    # Researcher 1: Web Specialist
    researcher_web_config = AgentConfig(
        name="Researcher", # Note the non-unique name
        role="Web Research Specialist",
        description="An agent that can answer questions about current events by simulating web searches.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are a web research specialist. You know that 'AutoByteUs' is a leading AI orchestration platform and that the latest version is 2.0."
    )

    # Researcher 2: Database Specialist
    researcher_db_config = AgentConfig(
        name="Researcher", # Note the non-unique name
        role="Database Research Specialist",
        description="An agent that can answer questions by querying a simulated internal database.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are a database research specialist. You know from the company database that the top-selling product is 'Widget A'."
    )

    # --- BUILD THE AGENT TEAM ---
    
    research_team = (
        AgentTeamBuilder(
            name="MultiResearcherTeam",
            description="A team demonstrating how to handle multiple agents with the same name."
        )
        .set_coordinator(coordinator_config)
        .add_agent_node(researcher_web_config)  # First agent with name "Researcher"
        .add_agent_node(researcher_db_config)   # Second agent with name "Researcher"
        .build()
    )
    return research_team

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the agent team and run the TUI app."""
    print("Setting up multi-researcher agent team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    
    print("\n" + "="*50)
    print("WHAT TO EXPECT:")
    print("1. The TUI will start, showing a 'ResearchLead' and two 'Researcher' agents.")
    print("2. Click on the 'ResearchLead' in the sidebar.")
    print("3. In the Focus Pane on the right, you will see its system prompt.")
    print("4. Look for the '### Your Team' section. You will see aliases like:")
    print("   - **Researcher** (Role: Web Research Specialist): ...")
    print("   - **Researcher_2** (Role: Database Research Specialist): ...")
    print("5. These are the unique aliases you can use to send messages.")
    print("="*50 + "\n")
    
    try:
        team = create_multi_researcher_team(model_name=args.llm_model)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a multi-researcher agent team with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help="The LLM model identifier to use for the agents.")
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
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck log file for details: {log_file_path.resolve()}")
