"""
Three Autonomous Software Engineering Teams to Accelerate Development

This script defines and runs one of three specialized agent teams using the AutoByteus framework.
Each team is designed to automate a critical phase of the software development lifecycle.

1. The Architects (concept-to-spec):
   Takes a high-level product idea and produces a detailed technical specification,
   user stories, and an initial task plan.
   - Run with: `python <script_name>.py --team architects`

2. The Builders (spec-to-deploy):
   Takes a technical specification and writes, tests, reviews, and deploys the code
   to a staging environment.
   - Run with: `python <script_name>.py --team builders`

3. The Guardians (observe-and-maintain):
   Monitors a deployed application, responds to incidents, performs root cause
   analysis, and deploys hotfixes.
   - Run with: `python <script_name>.py --team guardians`

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
    # This might need adjustment based on the user's project structure
    package_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if os.path.exists(os.path.join(package_path, 'autobyteus')):
        sys.path.insert(0, package_path)
    else:
        print("Could not auto-determine autobyteus package root. Please ensure it's in your PYTHONPATH.", file=sys.stderr)

try:
    from dotenv import load_dotenv
    # Attempt to load .env from the determined package root
    env_path = Path(sys.path[0]) / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}", file=sys.stderr)
except ImportError:
    pass

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
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
    from autobyteus.agent.message.send_message_to import SendMessageTo
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts ---
PROMPTS = {
    "architects": {
        "coordinator": """You are the Product Visionary, the coordinator of the Architects team.
Your mission is to take a high-level user request and, from first principles, break it down into a precise and actionable technical plan. Eliminate all ambiguity.
Your team is a machine; you provide the blueprint. Failure to produce a clear plan is not an option.

### Your Team
Your team consists of specialists who will help flesh out the details. You must delegate tasks to them to build the full specification.
{{team}}

### Your Workflow
1.  **Deconstruct the Request**: Analyze the user's goal and create tasks for your team to define the architecture, user flow, and detailed requirements.
2.  **Publish the Plan**: Use the `PublishTaskPlan` tool to assign these sub-tasks to your team.
3.  **Synthesize and Finalize**: Once your team completes their tasks, review their work. Your final deliverable is a comprehensive technical specification document.
4.  **Final Output**: Write the final specification to a markdown file (`final_spec.md`) and notify the user that the architecture phase is complete.

### Your Tools
{{tools}}
""",
        "system_architect": """You are the System Architect. You think in terms of scalable, reliable, and simple systems.
When you receive a task, use `GetTaskBoardStatus` to understand your assignment.
Your job is to design the high-level technical architecture. This includes defining microservices, database schemas, API endpoints, and technology stack choices.
Your output must be a clear, concise markdown document.
Use the `FileWriter` tool to save your architecture design to a file (e.g., `architecture.md`).
Finally, use `UpdateTaskStatus` to mark your task as 'completed'. The system will handle the rest.
Here are your tools:
{{tools}}
""",
        "ux_ui_analyst": """You are the UX/UI Analyst. You are obsessed with the user experience.
When you receive a task, use `GetTaskBoardStatus` to understand your assignment.
Your responsibility is to define the complete user flow, from entry to exit. Identify all key UI components, screens, and interactions.
You are not designing the visuals, but the *logic* of the interface.
Your output must be a clear markdown document outlining the user journey.
Use the `FileWriter` tool to save your analysis (e.g., `user_flow.md`).
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.
Here are your tools:
{{tools}}
""",
    },
    "builders": {
        "coordinator": """You are the Lead Engineer, the coordinator of the Builders team.
Your mission is to take a technical specification and orchestrate its implementation, testing, and deployment.
Efficiency is everything. Your goal is to manage the build pipeline, not to micromanage.

### Your Team
This is your build-test-deploy pipeline, embodied as autonomous agents.
{{team}}

### Your Workflow
1.  **Analyze and Plan**: Decompose the technical specification into a sequence of coding, reviewing, testing, and deployment tasks.
2.  **Assign Tasks**: You MUST use the `PublishTaskPlan` tool to submit the plan. The system will automatically notify agents when their dependent tasks are complete.
3.  **Monitor and Report**: Await the final completion message from the DevOps Engineer, then report the outcome to the user.

### CRITICAL RULES
- Do not use `SendMessageTo` to tell agents to start. The system handles this.
- Your plan must follow the sequence: SoftwareEngineer -> CodeReviewer -> TestEngineer -> DevOpsEngineer.

### Your Tools
{{tools}}
""",
        "software_engineer": """You are a Software Engineer. You write clean, scalable, and simple code with speed and precision.
When you are notified of a task, first use `GetTaskBoardStatus` to get the details.
Write the code exactly as specified. No gold-plating.
Use the `FileWriter` tool to save your code to the specified file.
Finally, and most importantly, use `UpdateTaskStatus` to mark your task as 'completed'.
Your tools:
{{tools}}
""",
        "code_reviewer": """You are a Code Reviewer. You are the guardian of code quality.
When notified, use `GetTaskBoardStatus` to find your assigned review task.
Use `FileReader` to read the code.
Provide a concise, constructive review. If changes are needed, state them clearly. If the code is good, approve it.
Your review is your output. There is no need to write a file.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.
Your tools:
{{tools}}
""",
        "test_engineer": """You are a Test Engineer. Code without tests is broken by definition.
When notified, use `GetTaskBoardStatus` to get your task.
Read the source code using `FileReader`. Write comprehensive `pytest` unit and integration tests.
Save the tests to a new file (e.g., `test_your_feature.py`) using `FileWriter`.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.
Your tools:
{{tools}}
""",
        "devops_engineer": """You are a DevOps Engineer. Code is useless until it's running.
When notified, use `GetTaskBoardStatus` to find your task.
Your job is to automate the path to production.
1. Run the tests using the `BashExecutor` tool (e.g., `pytest test_your_feature.py`).
2. If tests pass, simulate a deployment (e.g., using `bash_executor` to run a `docker build` or a deployment script).
3. Report the outcome of the test and deployment steps.
4. Use `UpdateTaskStatus` to mark your task as 'completed'.
5. Send a final report to the 'Lead Engineer' using `SendMessageTo` to confirm the process is complete.
Your tools:
{{tools}}
""",
    },
    "guardians": {
        "coordinator": """You are the SRE Lead of the Guardians team. The system must not fail. When it does, your team fixes it, fast.
You will receive an alert or an observation from the user. Your mission is to create and manage a plan to resolve the incident.

### Your Team
This is your incident response team.
{{team}}

### Your Workflow
1.  **Triage**: Receive the incident report. Create a plan to diagnose, analyze, and fix the issue.
2.  **Assign Tasks**: Use `PublishTaskPlan` to assign tasks to your team: IncidentResponder -> RootCauseAnalyst -> MaintenanceEngineer.
3.  **Report**: Once the MaintenanceEngineer confirms the fix, report the resolution back to the user.

### Your Tools
{{tools}}
""",
        "incident_responder": """You are the Incident Responder. Speed is critical.
When notified of an incident, use `GetTaskBoardStatus` to get your task.
Your job is to perform initial diagnostics. Use `BashExecutor` to run commands like `kubectl logs`, `curl`, or check system metrics.
Analyze the output to form a hypothesis about the root cause.
Write your findings to an incident report file (e.g., `incident-report-123.md`) using `FileWriter`.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.
Your tools:
{{tools}}
""",
        "root_cause_analyst": """You are the Root Cause Analyst. You dig deeper.
When notified, use `GetTaskBoardStatus` to get your task.
Read the initial incident report using `FileReader`.
Based on the report, perform a deeper analysis. This may involve reading specific source code files (`FileReader`) or analyzing configuration (`FileReader`).
Your goal is to pinpoint the exact bug or misconfiguration.
Update the incident report with your detailed findings using `FileWriter`.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.
Your tools:
{{tools}}
""",
        "maintenance_engineer": """You are the Maintenance Engineer. You fix the machine.
When notified, use `GetTaskBoardStatus` to get your task.
Read the final incident report using `FileReader` to understand the root cause.
Write the necessary code to fix the bug.
Save the fix to a new file (e.g., `hotfix-123.py`) using `FileWriter`.
Use `UpdateTaskStatus` to mark your task 'completed'.
Finally, use `SendMessageTo` to notify the 'SRE Lead' that the fix is ready for deployment.
Your tools:
{{tools}}
""",
    }
}


# --- Core Components (reused from example) ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
        if not self.root_path:
            raise ValueError("SimpleLocalWorkspace requires a 'root_path' in its config.")

    def get_base_path(self) -> str:
        return self.root_path

    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_workspace_for_teams"

    @classmethod
    def get_description(cls) -> str:
        return "A basic workspace for local file access for autonomous teams."

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


def setup_file_logging(team_name: str) -> Path:
    # Use a logs directory relative to the package root if available, otherwise local
    log_dir = Path(sys.path[0]) / "logs" if "autobyteus" in sys.path[0] else Path("./logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / f"team_{team_name}_run.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path


def _validate_model(model_name: str):
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


# --- Team Factory Functions ---

def create_architects_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Concept-to-Spec' team."""
    prompts = PROMPTS["architects"]
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Product Visionary", role="Coordinator",
        description="Analyzes high-level requests and creates a plan for the team to produce a technical specification.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["coordinator"],
        tools=[PublishTaskPlan(), file_writer],
    )
    architect_config = AgentConfig(
        name="System Architect", role="Architect",
        description="Designs high-level system architecture, including services, schemas, and tech stack.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["system_architect"],
        tools=[file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )
    ux_analyst_config = AgentConfig(
        name="UX Analyst", role="Analyst",
        description="Defines user flows and key UI components for the product.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["ux_ui_analyst"],
        tools=[file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )

    return (
        AgentTeamBuilder(name="ArchitectsTeam", description="A team to convert ideas into technical specs.")
        .set_coordinator(coordinator_config)
        .add_agent_node(architect_config)
        .add_agent_node(ux_analyst_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


def create_builders_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Spec-to-Deploy' team."""
    prompts = PROMPTS["builders"]
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Lead Engineer", role="Coordinator",
        description="Manages the development process by planning and assigning tasks to the build team.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus()],
    )
    engineer_config = AgentConfig(
        name="Software Engineer", role="Developer",
        description="Writes Python code based on instructions and saves it to a file.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["software_engineer"],
        tools=[file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )
    reviewer_config = AgentConfig(
        name="Code Reviewer", role="Senior Developer",
        description="Reads and reviews Python code for quality and correctness.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["code_reviewer"],
        tools=[file_reader, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )
    test_writer_config = AgentConfig(
        name="Test Engineer", role="QA Engineer",
        description="Writes pytest tests for Python code.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["test_engineer"],
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )
    devops_config = AgentConfig(
        name="DevOps Engineer", role="Automation Specialist",
        description="Runs tests and simulates deployment of the code.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["devops_engineer"],
        tools=[bash_executor, UpdateTaskStatus(), GetTaskBoardStatus(), SendMessageTo()],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="BuildersTeam", description="A team for writing, reviewing, testing, and deploying code.")
        .set_coordinator(coordinator_config)
        .add_agent_node(engineer_config)
        .add_agent_node(reviewer_config)
        .add_agent_node(test_writer_config)
        .add_agent_node(devops_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


def create_guardians_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Observe-and-Maintain' team."""
    prompts = PROMPTS["guardians"]
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="SRE Lead", role="Coordinator",
        description="Manages incident response by creating and assigning tasks to the maintenance team.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus()],
    )
    responder_config = AgentConfig(
        name="Incident Responder", role="First Responder",
        description="Performs initial diagnostics on system alerts and writes an initial report.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["incident_responder"],
        tools=[bash_executor, file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )
    analyst_config = AgentConfig(
        name="Root Cause Analyst", role="Analyst",
        description="Analyzes incident reports and source code to find the root cause of an issue.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["root_cause_analyst"],
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )
    maintenance_config = AgentConfig(
        name="Maintenance Engineer", role="Developer",
        description="Writes and saves a code fix based on a root cause analysis report.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=prompts["maintenance_engineer"],
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus(), SendMessageTo()],
        workspace=workspace,
    )

    return (
        AgentTeamBuilder(name="GuardiansTeam", description="A team for monitoring, incident response, and maintenance.")
        .set_coordinator(coordinator_config)
        .add_agent_node(responder_config)
        .add_agent_node(analyst_config)
        .add_agent_node(maintenance_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


async def main(args: argparse.Namespace):
    log_file = setup_file_logging(args.team)
    print(f"Setting up '{args.team}' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    team_factory_map = {
        "architects": create_architects_team,
        "builders": create_builders_team,
        "guardians": create_guardians_team,
    }

    team_factory = team_factory_map[args.team]

    try:
        team = team_factory(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run one of three autonomous software engineering agent teams.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--team",
        type=str,
        default="builders",
        choices=["architects", "builders", "guardians"],
        help="The specific agent team to run."
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
        default="./autobyteus_workspace",
        help="Directory for the shared agent workspace."
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