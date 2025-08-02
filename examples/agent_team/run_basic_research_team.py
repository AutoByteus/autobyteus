# file: autobyteus/examples/agent_team/run_basic_research_team.py
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

# --- Imports for the Agent Team Example ---
try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
    from autobyteus.cli.agent_team_tui.app import AgentTeamApp
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
def setup_file_logging(log_file_path: Path) -> None:
    """Configures file-based logging for the TUI session."""
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=log_file_path,
        filemode="w",
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    print(f"--> TUI logs will be written to: {log_file_path.resolve()}")


async def main(args: argparse.Namespace):
    """Main function to configure and run the research team."""
    print("--- Starting Basic Research Agent Team Example ---")

    # 1. Create LLM instance for the agents
    try:
        _ = LLMModel[args.llm_model]
    except KeyError:
        print(f"LLM Model '{args.llm_model}' is not valid. Use --help-models to see available models.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating LLM instance for model: {args.llm_model}")
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
            "You will be provided a manifest of your team members and available tools.\n\n"
            "{{tools}}"
        ),
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

    # 3. Define and Build the Agent Team using AgentTeamBuilder
    
    research_team = (
        AgentTeamBuilder(
            name="BasicResearchTeam",
            description="A simple two-agent team for delegating and answering research questions."
        )
        .set_coordinator(research_manager_config)
        .add_agent_node(fact_checker_config, dependencies=[])
        .build()
    )
    
    # 4. Run the Agent Team with the TUI
    
    print(f"Agent Team instance '{research_team.name}' created with ID: {research_team.team_id}")

    try:
        print("Starting interactive team TUI session...")
        app = AgentTeamApp(team=research_team)
        await app.run_async()
        print("Interactive team TUI session finished.")
    except Exception as e:
        logging.critical(f"An error occurred during the team execution: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details.")
    
    print("--- Basic Research Agent Team Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a basic two-agent research team with a TUI.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help="The LLM model to use for the agents.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--log-file", type=str, default="./logs/basic_research_team.log", 
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
    
    log_file = Path(parsed_args.log_file).resolve()
    setup_file_logging(log_file)

    try:
        asyncio.run(main(parsed_args))
    except (KeyboardInterrupt, SystemExit):
        logging.info("Script interrupted by user. Exiting.")
        print("\nExiting application.")
    except Exception as e:
        logging.critical(f"An unhandled error occurred at the top level: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
    finally:
        logging.info("Exiting script.")
