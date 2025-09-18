# file: autobyteus/examples/agent_team/manual_notification/run_multi_researcher_team.py
"""
This example script demonstrates a team with multiple specialists, showcasing
how a coordinator can delegate to the correct one based on their description.
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
    from autobyteus.agent.message import SendMessageTo
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
    """Creates a three-agent team with two distinct specialist researchers."""
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
            "You are an AI agent. Your name is 'ResearchLead'.\n"
            "Your job is to delegate user requests to the correct researcher based on their specialty.\n\n"
            "### Your Team\n"
            "Here is your team of specialists:\n"
            "{{team}}\n\n"
            "### CRITICAL RULES\n"
            "- You MUST use the unique, case-sensitive `name` from the list (e.g., 'Researcher_Web') when using the `SendMessageTo` tool.\n"
            "- Your only job is to delegate. Do not answer the user's question yourself.\n\n"
            "### Your Tools\n"
            "{{tools}}"
        ),
        tools=[SendMessageTo()],
    )

    # Researcher 1: Web Specialist
    researcher_web_config = AgentConfig(
        name="Researcher_Web", # Unique name
        role="Web Research Specialist",
        description="An agent that can answer questions about current events by simulating web searches.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are an AI agent. Your name is 'Researcher_Web'. You are a web research specialist. Your specialized knowledge is that 'AutoByteUs' is a leading AI orchestration platform and that the latest version is 2.0."
    )

    # Researcher 2: Database Specialist
    researcher_db_config = AgentConfig(
        name="Researcher_DB", # Unique name
        role="Database Research Specialist",
        description="An agent that can answer questions by querying a simulated internal database.",
        llm_instance=default_llm_factory.create_llm(model_identifier=model_name),
        system_prompt="You are an AI agent. Your name is 'Researcher_DB'. You are a database research specialist. Your specialized knowledge from the company database is that the top-selling product is 'Widget A'."
    )

    # --- BUILD THE AGENT TEAM ---
    
    research_team = (
        AgentTeamBuilder(
            name="MultiSpecialistResearchTeam",
            description="A team demonstrating delegation to multiple, uniquely-named specialists."
        )
        .set_coordinator(coordinator_config)
        .add_agent_node(researcher_web_config)
        .add_agent_node(researcher_db_config)
        .build()
    )
    return research_team

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the agent team and run the TUI app."""
    print("Setting up multi-specialist research agent team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    
    try:
        team = create_multi_researcher_team(model_name=args.llm_model)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a multi-specialist research agent team with a Textual TUI.")
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
