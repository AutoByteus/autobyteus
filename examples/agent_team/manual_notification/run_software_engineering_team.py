# file: autobyteus/examples/agent_team/manual_notification/run_software_engineering_team.py
"""
This example script demonstrates a simple software development agent team
with a coordinator, an engineer, a code reviewer, a test writer, and a tester.
It showcases a notification-based communication protocol.
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
PROMPTS_DIR = SCRIPT_DIR / "prompts" / "software_engineering"
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
    from autobyteus.tools import file_writer, file_reader, bash_executor
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
    from autobyteus.task_management.tools import (
        PublishTaskPlan,
        GetTaskBoardStatus,
        UpdateTaskStatus,
    )
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- A simple, self-contained workspace for this example ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    """A minimal workspace for local file system access."""

    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
        if not self.root_path:
            raise ValueError("SimpleLocalWorkspace requires a 'root_path' in its config.")

    def get_base_path(self) -> str:
        return self.root_path

    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_workspace_for_review"

    @classmethod
    def get_description(cls) -> str:
        return "A basic workspace for local file access for the code review team."

    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="root_path",
            param_type=ParameterType.STRING,
            description="The absolute local file path for the workspace root.",
            required=True
        ))
        return schema


# --- Logging Setup ---
def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "software_engineering_team_tui_app.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

def _validate_model(model_name: str):
    """Validates that a model identifier is available in the factory."""
    try:
        _ = LLMModel[model_name]
    except (KeyError, ValueError):
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid or ambiguous.", file=sys.stderr)
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with model arguments):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Display Name: {model.name:<30} Identifier: {model.model_identifier}")
        except Exception as e:
            print(f"Additionally, an error occurred while listing models: {e}", file=sys.stderr)
        sys.exit(1)

def load_prompt(filename: str) -> str:
    """Loads a prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {prompt_path}")
        print(f"CRITICAL ERROR: Prompt file not found at {prompt_path}", file=sys.stderr)
        raise
    except Exception as e:
        logging.error(f"Error reading prompt file {prompt_path}: {e}")
        print(f"CRITICAL ERROR: Could not read prompt file at {prompt_path}: {e}", file=sys.stderr)
        raise

def create_code_review_team(
    coordinator_model: str, 
    engineer_model: str, 
    reviewer_model: str, 
    test_writer_model: str,
    tester_model: str,
    workspace: BaseAgentWorkspace
):
    """Creates the code review agent team."""
    
    # --- AGENT CONFIGURATIONS ---

    # Coordinator Agent
    coordinator_config = AgentConfig(
        name="Project Manager", role="Coordinator", description="Manages the development process by planning and assigning tasks to the team.",
        llm_instance=default_llm_factory.create_llm(model_identifier=coordinator_model),
        system_prompt=load_prompt("coordinator.prompt"),
        tools=[PublishTaskPlan(), GetTaskBoardStatus()],
    )

    # Software Engineer Agent
    engineer_config = AgentConfig(
        name="Software Engineer", role="Developer", description="Writes Python code based on instructions and saves it to a file.",
        llm_instance=default_llm_factory.create_llm(model_identifier=engineer_model),
        system_prompt=load_prompt("software_engineer.prompt"),
        tools=[file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )
    
    # Code Reviewer Agent
    reviewer_config = AgentConfig(
        name="Code Reviewer", role="Senior Developer", description="Reads and reviews Python code from files for quality and correctness.",
        llm_instance=default_llm_factory.create_llm(model_identifier=reviewer_model),
        system_prompt=load_prompt("code_reviewer.prompt"),
        tools=[file_reader, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )

    # Test Writer Agent
    test_writer_config = AgentConfig(
        name="Test Writer", role="QA Engineer", description="Writes pytest tests for Python code.",
        llm_instance=default_llm_factory.create_llm(model_identifier=test_writer_model),
        system_prompt=load_prompt("test_writer.prompt"),
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )

    # Tester Agent
    tester_config = AgentConfig(
        name="Tester", role="QA Automation", description="Executes pytest tests and reports results.",
        llm_instance=default_llm_factory.create_llm(model_identifier=tester_model),
        system_prompt=load_prompt("tester.prompt"),
        tools=[bash_executor, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )


    # --- BUILD THE AGENT TEAM ---
    
    code_review_team = (
        AgentTeamBuilder(name="SoftwareDevTeam", description="A team for writing, reviewing, and testing code.")
        .set_coordinator(coordinator_config)
        .add_agent_node(engineer_config)
        .add_agent_node(reviewer_config)
        .add_agent_node(test_writer_config)
        .add_agent_node(tester_config)
        .build()
    )

    return code_review_team

async def main(args: argparse.Namespace, log_file: Path):
    """Main async function to create the agent team and run the TUI app."""
    print("Setting up software development team (MANUAL NOTIFICATION MODE)...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace (output directory) is set to: {workspace_path}")
    
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    # Resolve models
    coordinator_model = args.coordinator_model or args.llm_model
    engineer_model = args.engineer_model or args.llm_model
    reviewer_model = args.reviewer_model or args.llm_model
    test_writer_model = args.test_writer_model or args.llm_model
    tester_model = args.tester_model or args.llm_model
    
    # Validate all model identifiers before proceeding
    for model_id in [coordinator_model, engineer_model, reviewer_model, test_writer_model, tester_model]:
        _validate_model(model_id)

    print(f"--> Coordinator Model: {coordinator_model}")
    print(f"--> Engineer Model: {engineer_model}")
    print(f"--> Reviewer Model: {reviewer_model}")
    print(f"--> Test Writer Model: {test_writer_model}")
    print(f"--> Tester Model: {tester_model}")

    try:
        team = create_code_review_team(
            coordinator_model=coordinator_model,
            engineer_model=engineer_model,
            reviewer_model=reviewer_model,
            test_writer_model=test_writer_model,
            tester_model=tester_model,
            workspace=workspace
        )
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a software development agent team with a Textual TUI (Manual Notification Mode).",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The default LLM model identifier for all agents.")
    parser.add_argument("--coordinator-model", type=str, help="Specific LLM model for the ProjectManager. Defaults to --llm-model.")
    parser.add_argument("--engineer-model", type=str, help="Specific LLM model for the SoftwareEngineer. Defaults to --llm-model.")
    parser.add_argument("--reviewer-model", type=str, help="Specific LLM model for the CodeReviewer. Defaults to --llm-model.")
    parser.add_argument("--test-writer-model", type=str, help="Specific LLM model for the TestWriter. Defaults to --llm-model.")
    parser.add_argument("--tester-model", type=str, help="Specific LLM model for the Tester. Defaults to --llm-model.")
    parser.add_argument("--output-dir", type=str, default="./code_review_output", help="Directory for the shared workspace.")
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
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck log file for details: {log_file_path.resolve()}")
