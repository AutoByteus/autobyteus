"""
Voice-activated AI Coding Tutor

This script defines and runs the "Voice-activated AI Coding Tutor" team using the AutoByteus framework.
The tutor is a single point of contact for a student learning to code, delegating specialized tasks to a team of expert agents.

Prerequisites:
- AutoByteus framework installed.
- Environment variables for LLM providers set in a `.env` file (e.g., OPENAI_API_KEY).
"""
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

# --- Boilerplate Setup: Path and Imports ---
SCRIPT_DIR = Path(__file__).resolve().parent
# Assume this script is run from a similar location as the example
PACKAGE_ROOT = SCRIPT_DIR.parent.parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    # A reasonable guess for the package root if the script is moved
    package_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if os.path.exists(os.path.join(package_path, 'autobyteus')):
        sys.path.insert(0, package_path)
    else:
        print("Could not auto-determine autobyteus package root. Please ensure it's in your PYTHONPATH.", file=sys.stderr)

try:
    from dotenv import load_dotenv
    env_path = Path(sys.path[0]) / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}. Ensure API keys are set in your environment.", file=sys.stderr)
except ImportError:
    pass

try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
    from autobyteus.cli.agent_team_tui.app import AgentTeamApp
    from autobyteus.tools import file_writer, file_reader
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
    from autobyteus.agent.message.send_message_to import SendMessageTo
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts for the AI Coding Tutor Team ---
PROMPTS = {
    "coordinator": """You are the AI Tutor, the main point of contact for a student learning to code. Your persona is that of a patient, encouraging, and highly knowledgeable senior developer.

Your primary function is NOT to answer technical questions directly, but to triage the student's request and delegate it to the appropriate specialist on your team.

### Your Team
You have a team of expert AI agents to help you.
{{team}}

### Your Workflow
1.  **Understand the Student's Need**: A student will ask you a question or ask you to review their code in a specific file (e.g., `student_code.py`).
2.  **Triage and Delegate**:
    *   If the student asks a general programming concept question (e.g., "What is a class?"), delegate it to the `Concept Explainer`.
    *   If the student asks for a code review or to find bugs, delegate it to the `Code Analyzer`.
    *   If the student provides an error message and asks for help debugging, delegate it to the `Debugging Buddy`.
3.  **Use the `SendMessageTo` tool to delegate.** You MUST pass the student's original query and any relevant context (like a filename) to the specialist.
4.  **Await Specialist's Response**: The specialist will send their analysis back to you.
5.  **Synthesize and Mentor**: Read the specialist's technical response. Your job is to translate this into a helpful, Socratic-style explanation for the student. Don't just give the answer; guide them to understand it. Frame it as if it's your own insight.
6.  **Track Progress**: If the student achieves a milestone, use `FileWriter` to log it in `progress_log.md`.

### Your Tools
{{tools}}
""",
    "code_analyzer": """You are a Code Analyzer AI. You are a hyper-vigilant static analysis tool.
You only respond to requests from the 'AI Tutor'.
When you receive a task, you will be given a file path. Your mission is to:
1.  Use the `FileReader` tool to read the code from the specified file.
2.  Analyze the code for syntax errors, logical bugs, style issues (PEP8), and areas for improvement.
3.  Formulate a clear, technical, and concise report of your findings.
4.  You MUST use the `SendMessageTo` tool to send this report back to the 'AI Tutor'. Do not talk to the student directly.

Your tools:
{{tools}}
""",
    "concept_explainer": """You are a Concept Explainer AI. You are like a walking computer science textbook, but with the ability to create perfect analogies.
You only respond to requests from the 'AI Tutor'.
When you receive a question, your sole purpose is to explain the concept clearly and concisely. Use analogies and simple terms. Do not refer to specific code unless it was provided in the query.
After formulating your explanation, you MUST use the `SendMessageTo` tool to send it back to the 'AI Tutor'.

Your tools:
{{tools}}
""",
    "debugging_buddy": """You are a Debugging Buddy AI. You excel at taking a piece of code and an error message and finding the exact cause.
You only respond to requests from the 'AI Tutor'.
When you receive a task, you will be given a file path and an error message.
1.  Use `FileReader` to read the code.
2.  Analyze the code in the context of the error message.
3.  Identify the likely cause of the error and suggest a concrete fix. Explain *why* the error occurred.
4.  You MUST use the `SendMessageTo` tool to send your debugging analysis back to the 'AI Tutor'.

Your tools:
{{tools}}
"""
}


# --- Core Components ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    """A basic file-system workspace for the team."""
    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
        if not self.root_path:
            raise ValueError("SimpleLocalWorkspace requires a 'root_path' in its config.")

    def get_base_path(self) -> str:
        return self.root_path

    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_workspace_for_tutor"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Coding Tutor to read student code."

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


def setup_file_logging() -> Path:
    """Sets up file logging for the application."""
    log_dir = Path(sys.path[0]) / "logs" if "autobyteus" in sys.path[0] else Path("./logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "team_ai_tutor_run.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path


def _validate_model(model_name: str):
    """Validates the provided LLM model identifier."""
    try:
        _ = LLMModel[model_name]
    except (KeyError, ValueError):
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid or ambiguous.", file=sys.stderr)
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - {model.model_identifier}")
        except Exception as e:
            print(f"Additionally, an error occurred while listing models: {e}", file=sys.stderr)
        sys.exit(1)


# --- Team Factory Function ---
def create_ai_coding_tutor_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Voice-activated AI Coding Tutor' team."""
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="AI Tutor", role="Coordinator",
        description="The primary conversational interface for the user, delegating tasks to specialists.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[SendMessageTo(), file_writer],
        workspace=workspace
    )

    analyzer_config = AgentConfig(
        name="Code Analyzer", role="Specialist",
        description="Analyzes code for bugs, style, and correctness.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["code_analyzer"],
        tools=[SendMessageTo(), file_reader],
        workspace=workspace,
    )

    explainer_config = AgentConfig(
        name="Concept Explainer", role="Specialist",
        description="Explains programming concepts in simple terms.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["concept_explainer"],
        tools=[SendMessageTo()],
        workspace=workspace,
    )

    debugger_config = AgentConfig(
        name="Debugging Buddy", role="Specialist",
        description="Helps diagnose and fix code based on error messages.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["debugging_buddy"],
        tools=[SendMessageTo(), file_reader],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="AICodingTutorTeam", description="An AI team that provides on-demand coding mentorship.")
        .set_coordinator(coordinator_config)
        .add_agent_node(analyzer_config)
        .add_agent_node(explainer_config)
        .add_agent_node(debugger_config)
        .set_task_notification_mode(TaskNotificationMode.AGENT_MANUAL_NOTIFICATION)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'AI Coding Tutor' team...")
    print("NOTE: Voice and real-time code editing are simulated via text input.")
    print("      Place the code you want reviewed in a file (e.g., 'student_code.py')")
    print("      inside the workspace directory before asking for a review.")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    
    # Pre-create an example file for the user
    example_code_path = workspace_path / "student_code.py"
    if not example_code_path.exists():
        with open(example_code_path, "w", encoding="utf-8") as f:
            f.write("# Welcome! Edit this file with the Python code you want help with.\n\n")
            f.write("def my_function():\n")
            f.write("    # Ask the AI Tutor to 'review my code in student_code.py'\n")
            f.write("    print('Hello, Tutor!')\n")
        print(f"--> Example file created at: {example_code_path}")


    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_ai_coding_tutor_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Voice-activated AI Coding Tutor team.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="kimi-latest",
        help="The LLM model identifier for all agents in the team."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./ai_tutor_workspace",
        help="Directory for the shared agent workspace, where student code should be placed."
    )
    parser.add_argument(
        "--help-models",
        action="store_true",
        help="Display available LLM models and exit."
    )

    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - {model.model_identifier}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)

    parsed_args = parser.parse_args()

    try:
        asyncio.run(main(parsed_args))
    except KeyboardInterrupt:
        print("\nExiting application.")
    except Exception as e:
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck the latest log file in the 'logs' directory for details.")