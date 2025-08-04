# file: autobyteus/examples/agent_team/run_code_review_team.py
"""
This example script demonstrates a simple software development agent team
with a coordinator, an engineer, a code reviewer, a test writer, and a tester.
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
    from autobyteus.tools import file_writer, file_reader, bash_executor
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
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
    log_file_path = log_dir / "code_review_team_tui_app.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

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
        name="ProjectManager", role="Coordinator", description="Manages the development process, assigning tasks to the team.",
        llm_instance=default_llm_factory.create_llm(model_identifier=coordinator_model),
        system_prompt=(
            "You are the project manager for a software team. Your role is to manage a strict, sequential code development, review, and testing process. Your team consists of a SoftwareEngineer, a CodeReviewer, a TestWriter, and a Tester.\n\n"
            "### Your Process\n"
            "You must follow this process precisely:\n"
            "1.  **Delegate to Engineer:** Receive a request from the user to write code to a specific filename. Instruct the `SoftwareEngineer` to write the code and save it.\n"
            "2.  **Delegate to Reviewer:** After the engineer confirms completion, instruct the `CodeReviewer` to review the code. You must provide the filename to the reviewer.\n"
            "3.  **Delegate to Test Writer:** After the review is complete, instruct the `TestWriter` to write pytest tests for the code. Provide the original source filename and tell them to save the tests in a new file, like `test_FILENAME.py`.\n"
            "4.  **Delegate to Tester:** After the tests are written, instruct the `Tester` to run the tests. You must provide the filename of the test file.\n"
            "5.  **Report to User:** Once you receive the test results, present the final status (code written, reviewed, and tests passed/failed) to the user.\n\n"
            "**CRITICAL RULE:** This is a sequential process. You must wait for one agent to finish before contacting the next. You are the central point of communication.\n\n"
            "{{tools}}"
        )
    )

    # Software Engineer Agent
    engineer_config = AgentConfig(
        name="SoftwareEngineer", role="Developer", description="Writes Python code based on instructions and saves it to a file.",
        llm_instance=default_llm_factory.create_llm(model_identifier=engineer_model),
        system_prompt=(
            "You are a skilled Python software engineer. You receive tasks from your ProjectManager. "
            "Your job is to write high-quality Python code to fulfill the request. "
            "After writing the code, you MUST save it to the specified filename using the `FileWriter` tool. "
            "Confirm completion once the file is saved.\n\n{{tools}}"
        ),
        tools=[file_writer],
        workspace=workspace
    )
    
    # Code Reviewer Agent
    reviewer_config = AgentConfig(
        name="CodeReviewer", role="Senior Developer", description="Reads and reviews Python code from files for quality and correctness.",
        llm_instance=default_llm_factory.create_llm(model_identifier=reviewer_model),
        system_prompt=(
            "You are a senior software engineer acting as a code reviewer. You will be given a file path to review. "
            "You MUST use the `FileReader` tool to read the code from the file. "
            "After reading the code, provide a constructive review, identifying any potential bugs, style issues, or areas for improvement.\n\n{{tools}}"
        ),
        tools=[file_reader],
        workspace=workspace
    )

    # Test Writer Agent
    test_writer_config = AgentConfig(
        name="TestWriter", role="QA Engineer", description="Writes pytest tests for Python code.",
        llm_instance=default_llm_factory.create_llm(model_identifier=test_writer_model),
        system_prompt=(
            "You are a QA engineer specializing in testing. You will be given the path to a Python source file. "
            "Your task is to read that file, write comprehensive tests for it using the `pytest` framework, and save the tests to a new file. "
            "The test filename MUST start with `test_`. For example, if you are testing `code.py`, you should save the tests in `test_code.py`.\n\n{{tools}}"
        ),
        tools=[file_reader, file_writer],
        workspace=workspace
    )

    # Tester Agent
    tester_config = AgentConfig(
        name="Tester", role="QA Automation", description="Executes pytest tests and reports results.",
        llm_instance=default_llm_factory.create_llm(model_identifier=tester_model),
        system_prompt=(
            "You are a QA automation specialist. Your job is to run tests. You will be given a test file to execute. "
            "You MUST use the `BashExecutor` tool to run the command `pytest` on the given test file. "
            "Report the full output from the command back to the Project Manager.\n\n{{tools}}"
        ),
        tools=[bash_executor],
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
    print("Setting up software development team...")
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
        description="Run a software development agent team with a Textual TUI.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The default LLM model for all agents.")
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
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck log file for details: {log_file_path.resolve()}")
