# file: autobyteus/examples/agent_team/run_debate_team.py
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

def create_debate_team(moderator_model: str, affirmative_model: str, negative_model: str, use_xml_tool_format: bool = True):
    """Creates a hierarchical debate team for the TUI demonstration."""
    # Validate models
    def _validate_model(model_name: str):
        try:
            _ = LLMModel[model_name]
        except KeyError:
            logging.critical(f"LLM Model '{model_name}' is not valid. Use --help-models to see available models.")
            print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid. Use --help-models to see available models.\nCheck log file for details.")
            sys.exit(1)

    for model in [moderator_model, affirmative_model, negative_model]:
        _validate_model(model)
    
    logging.info(f"Using models -> Moderator: {moderator_model}, Affirmative: {affirmative_model}, Negative: {negative_model}")
    logging.info(f"Using XML tool format: {use_xml_tool_format}")

    # --- AGENT CONFIGURATIONS ---

    # Parent-Level Agents
    moderator_config = AgentConfig(
        name="DebateModerator", role="Coordinator", description="Manages the debate, gives turns, and summarizes.",
        llm_instance=default_llm_factory.create_llm(model_identifier=moderator_model),
        system_prompt=(
            "You are the impartial moderator of a debate between two teams. Your goal is to facilitate a structured, turn-by-turn debate on a user's topic.\n"
            "Your team consists of Team_Affirmative and Team_Negative. You will delegate tasks to them using their unique names.\n"
            "Responsibilities: 1. Announce the topic. 2. Ask Team_Affirmative for an opening statement. 3. Ask Team_Negative for a rebuttal. "
            "4. Facilitate a structured flow of arguments. 5. Conclude the debate.\n"
            "CRITICAL RULE: You must enforce a strict turn-based system. Only communicate with ONE team at a time using the `SendMessageTo` tool. After sending a message, you must wait for a response before messaging the other team.\n"
            "Do not debate yourself. Your role is to moderate.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    # Team Affirmative Agents
    lead_affirmative_config = AgentConfig(
        name="Lead_Affirmative", role="Coordinator", description="Leads the team arguing FOR the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=affirmative_model),
        system_prompt=(
            "You are the lead of the Affirmative team. You receive high-level instructions from the DebateModerator (e.g., 'prepare opening statement').\n"
            "Your job is to delegate this task to your team member, the Proponent, by giving them a specific instruction.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )
    proponent_config = AgentConfig(
        name="Proponent", role="Debater", description="Argues in favor of the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=affirmative_model),
        system_prompt="You are a Proponent. You will receive instructions from your team lead. Your role is to argue STRONGLY and PERSUASIVELY IN FAVOR of the motion.",
        use_xml_tool_format=use_xml_tool_format
    )

    # Team Negative Agents
    lead_negative_config = AgentConfig(
        name="Lead_Negative", role="Coordinator", description="Leads the team arguing AGAINST the motion.",
        llm_instance=default_llm_factory.create_llm(model_identifier=negative_model),
        system_prompt=(
            "You are the lead of the Negative team. You receive high-level instructions from the DebateModerator (e.g., 'prepare your rebuttal').\n"
            "Your job is to delegate this task to your team member, the Opponent, by giving them a specific instruction.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )
    opponent_config = AgentConfig(
        name="Opponent", role="Debater", description="Argues against the debate topic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=negative_model),
        system_prompt="You are an Opponent. You will receive instructions from your team lead. Your role is to argue STRONGLY and PERSUASIVELY AGAINST the motion.",
        use_xml_tool_format=use_xml_tool_format
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

    # Determine tool format setting from args
    use_xml_tool_format = not args.no_xml_tools
    print(f"--> Using XML Tool Format: {use_xml_tool_format}")

    try:
        team = create_debate_team(
            moderator_model=moderator_model,
            affirmative_model=affirmative_model,
            negative_model=negative_model,
            use_xml_tool_format=use_xml_tool_format,
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
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The default LLM model for all agents. Can be overridden by other arguments.")
    parser.add_argument("--moderator-model", type=str, help="Specific LLM model for the Moderator. Defaults to --llm-model.")
    parser.add_argument("--affirmative-model", type=str, help="Specific LLM model for the Affirmative Team. Defaults to --llm-model.")
    parser.add_argument("--negative-model", type=str, help="Specific LLM model for the Negative Team. Defaults to --llm-model.")
    parser.add_argument("--no-xml-tools", action="store_true", help="Disable XML-based tool formatting. Recommended for models that struggle with XML.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    
    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized()
            print("Available LLM Models (you can use either name or value with model arguments):")
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
