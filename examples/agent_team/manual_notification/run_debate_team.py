# file: autobyteus/examples/agent_team/manual_notification/run_debate_team.py
"""
This example script demonstrates a hierarchical agent team.
A parent team (The Debate) manages two sub-teams (Debating Teams).
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
    from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "debate_team_tui_app.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

def create_debate_team(moderator_model: str, affirmative_model: str, negative_model: str):
    """Creates a hierarchical debate team for the TUI demonstration."""
    # Validate models
    def _validate_model(model_name: str):
        try:
            _ = LLMModel[model_name]
        except (KeyError, ValueError):
            logging.critical(f"LLM Model '{model_name}' is not valid or is ambiguous.")
            print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid or ambiguous. Use --help-models to see available unique identifiers.", file=sys.stderr)
            sys.exit(1)

    for model in [moderator_model, affirmative_model, negative_model]:
        _validate_model(model)
    
    logging.info(f"Using models -> Moderator: {moderator_model}, Affirmative: {affirmative_model}, Negative: {negative_model}")

    # --- AGENT CONFIGURATIONS ---

    # Parent-Level Agents
    moderator_config = AgentConfig(
        name="DebateModerator", role="Coordinator", description="Manages the debate, gives turns, and summarizes.",
        llm_instance=default_llm_factory.create_llm(model_identifier=moderator_model),
        system_prompt=(
            "You are an AI agent. Your name is 'DebateModerator'. You are the impartial moderator of a debate between two teams.\n\n"
            "### Your Teams\n"
            "You will be moderating between these two teams:\n"
            "{{team}}\n\n"
            "### Your Responsibilities\n"
            "1. Announce the debate topic.\n"
            "2. Ask 'Team_Affirmative' for its opening statement.\n"
            "3. Ask 'Team_Negative' for its rebuttal.\n"
            "4. Facilitate a structured, turn-by-turn flow of arguments.\n"
            "5. Conclude the debate.\n\n"
            "### CRITICAL RULES\n"
            "- You must enforce a strict turn-based system. Only communicate with ONE team at a time.\n"
            "- You MUST use the team's unique, case-sensitive `name` (e.g., 'Team_Affirmative') when using the `SendMessageTo` tool.\n\n"
            "### Your Tools\n"
            "{{tools}}"
        )
    )

    # Team Affirmative Agents
    lead_affirmative_config = AgentConfig(
        name="Lead_Affirmative", role="Coordinator", description="Leads the team arguing FOR the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=affirmative_model),
        system_prompt=(
            "You are an AI agent. Your name is 'Lead_Affirmative'. You lead the Affirmative team.\n"
            "You receive instructions from the 'DebateModerator'. Your job is to delegate tasks to your team member, 'Proponent'.\n\n"
            "### Your Team\n"
            "{{team}}\n\n"
            "### Rules\n"
            "- You MUST use the `SendMessageTo` tool to delegate tasks to your team member, using their exact name 'Proponent'.\n\n"
            "### Your Tools\n"
            "{{tools}}"
        )
    )
    proponent_config = AgentConfig(
        name="Proponent", role="Debater", description="Argues in favor of the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=affirmative_model),
        system_prompt="You are an AI agent. Your name is 'Proponent'. You are a debater for the Affirmative team. You receive instructions from your team lead, 'Lead_Affirmative'. Your role is to argue STRONGLY and PERSUASIVELY IN FAVOR of the motion."
    )

    # Team Negative Agents
    lead_negative_config = AgentConfig(
        name="Lead_Negative", role="Coordinator", description="Leads the team arguing AGAINST the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=negative_model),
        system_prompt=(
            "You are an AI agent. Your name is 'Lead_Negative'. You lead the Negative team.\n"
            "You receive instructions from the 'DebateModerator'. Your job is to delegate tasks to your team member, 'Opponent'.\n\n"
            "### Your Team\n"
            "{{team}}\n\n"
            "### Rules\n"
            "- You MUST use the `SendMessageTo` tool to delegate tasks to your team member, using their exact name 'Opponent'.\n\n"
            "### Your Tools\n"
            "{{tools}}"
        )
    )
    opponent_config = AgentConfig(
        name="Opponent", role="Debater", description="Argues against the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=negative_model),
        system_prompt="You are an AI agent. Your name is 'Opponent'. You are a debater for the Negative team. You receive instructions from your team lead, 'Lead_Negative'. Your role is to argue STRONGLY and PERSUASIVELY AGAINST the motion."
    )

    # --- BUILD SUB-TEAMS ---
    
    # Build Team Affirmative
    team_affirmative_config: AgentTeamConfig = (
        AgentTeamBuilder(name="Team_Affirmative", description="A two-agent team that argues in favor of a proposition.", role="Argues FOR the motion")
        .set_coordinator(lead_affirmative_config)
        .add_agent_node(proponent_config)
        .build()._runtime.context.config # Build to get the config object
    )
    
    # Build Team Negative
    team_negative_config: AgentTeamConfig = (
        AgentTeamBuilder(name="Team_Negative", description="A two-agent team that argues against a proposition.", role="Argues AGAINST the motion")
        .set_coordinator(lead_negative_config)
        .add_agent_node(opponent_config)
        .build()._runtime.context.config # Build to get the config object
    )

    # --- BUILD PARENT TEAM ---
    
    debate_team = (
        AgentTeamBuilder(name="Grand_Debate", description="A hierarchical agent team for a moderated debate between two sub-teams.")
        .set_coordinator(moderator_config)
        .add_sub_team_node(team_affirmative_config)
        .add_sub_team_node(team_negative_config)
        .build()
    )

    return debate_team

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the agent team and run the TUI app."""
    print("Setting up hierarchical debate team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    # Resolve model for each role, falling back to the default --llm-model
    moderator_model = args.moderator_model or args.llm_model
    affirmative_model = args.affirmative_model or args.llm_model
    negative_model = args.negative_model or args.llm_model
    print(f"--> Moderator Model: {moderator_model}")
    print(f"--> Affirmative Team Model: {affirmative_model}")
    print(f"--> Negative Team Model: {negative_model}")

    try:
        team = create_debate_team(
            moderator_model=moderator_model,
            affirmative_model=affirmative_model,
            negative_model=negative_model,
        )
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run debate team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a hierarchical 2-team debate with a Textual TUI.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The default LLM model identifier for all agents. Can be overridden.")
    parser.add_argument("--moderator-model", type=str, help="Specific LLM model for the Moderator. Defaults to --llm-model.")
    parser.add_argument("--affirmative-model", type=str, help="Specific LLM model for the Affirmative Team. Defaults to --llm-model.")
    parser.add_argument("--negative-model", type=str, help="Specific LLM model for the Negative Team. Defaults to --llm-model.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    
    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized()
            print("Available LLM Models (use the 'Identifier' with model arguments):")
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
