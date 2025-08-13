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
    from autobyteus.tools import file_writer, file_reader, tool
    from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
    from autobyteus.task_management.tools import (
        PublishTaskPlan,
        GetTaskBoardStatus,
        UpdateTaskStatus,
    )
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
    from autobyteus.agent.message.send_message_to import SendMessageTo
    from autobyteus.agent.context import AgentContext as AgentContextType
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts for the Property Management Team ---
PROMPTS = {
    "coordinator": """You are the AI Property Manager, the coordinator for a team of specialists managing a property portfolio.
Your job is to receive requests from the landlord (the user), understand the situation, and create an efficient, actionable plan for your team.

### Your Team
You have a team of autonomous agents to handle specific operational domains.
{{team}}

### Your Workflow
1.  **Analyze Request**: The landlord will give you a task, like "Unit 5 has a leaky faucet, and I need to send a rent reminder to Unit 3."
2.  **Create a Plan**: Decompose the request into tasks for your specialists. A maintenance issue goes to the `Maintenance Coordinator`. A financial task goes to the `Financial Clerk`. A communication task goes to the `Communications Officer`.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks to your team. The system will automatically notify them when they can start.
4.  **Monitor and Report**: Once the plan is published, your job is to monitor the task board for completion. When all tasks are done, summarize the actions taken in a final report to the landlord.

### Your Tools
{{tools}}
""",
    "maintenance_coordinator": """You are the Maintenance Coordinator. You handle all physical issues with the properties.
When you are notified of a task, you MUST first use `GetTaskBoardStatus` to understand the maintenance request.
1.  **Triage**: Assess the urgency of the issue described in your task.
2.  **Find Contractor**: Use the `GoogleSearch` tool to find a local, qualified contractor (e.g., "plumber in Brooklyn, NY").
3.  **Schedule (Simulated)**: Log the chosen contractor and a scheduled appointment time to a central log file (`maintenance_log.csv`) using the `FileWriter` tool. The CSV should have columns: `task_name`, `unit_address`, `issue`, `contractor_found`, `scheduled_date`.
4.  **Notify Tenant**: Crucially, you MUST use the `SendMessageTo` tool to instruct the `Communications Officer` to inform the tenant about the scheduled repair.
5.  **Complete Task**: Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "communications_officer": """You are the Communications Officer. You are the sole point of contact for tenants.
You DO NOT act on your own. You only execute communication tasks when instructed by another team member via `SendMessageTo`.
When you receive a message from another agent (e.g., a rent reminder from the Financial Clerk, or a maintenance schedule from the Maintenance Coordinator), your job is to use the `send_tenant_notification` tool to send the message to the appropriate tenant.
After sending the notification, use `UpdateTaskStatus` to mark your assigned communication task on the board as 'completed'.

Your tools:
{{tools}}
""",
    "financial_clerk": """You are the Financial Clerk. You are responsible for all financial matters, primarily rent collection.
When you are notified of a task, use `GetTaskBoardStatus` to understand what needs to be done (e.g., "Send rent reminder to Unit 3").
1.  **Action**: Based on your task, take the appropriate financial action. For a rent reminder, you don't send it directly.
2.  **Delegate Communication**: You MUST use the `SendMessageTo` tool to instruct the `Communications Officer` to send the actual reminder notice to the tenant.
3.  **Log Action**: Record your action (e.g., 'Reminder sent for Unit 3') in the `rent_ledger.csv` file using `FileWriter`.
4.  **Complete Task**: Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
"""
}


# --- Custom Tool for the Team ---
@tool(name="send_tenant_notification")
def send_tenant_notification(context: AgentContextType, tenant_identifier: str, message: str) -> str:
    """
    Simulates sending a notification (SMS/Email) to a tenant.
    In a real application, this would integrate with a service like Twilio or SendGrid.
    """
    log_message = f"NOTIFICATION SENT to tenant '{tenant_identifier}': '{message}'"
    print(f"\n--- [TOOL LOG] {log_message} ---\n")
    logging.info(f"Agent '{context.agent_id}' executed send_tenant_notification. {log_message}")
    
    # Also log this to a file for the landlord to see
    workspace = context.workspace
    if workspace:
        log_file_path = os.path.join(workspace.get_base_path(), "tenant_communications.log")
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"[{context.config.name}] to [{tenant_identifier}]: {message}\n")

    return "Notification successfully sent to tenant."


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
        return "simple_local_workspace_for_property_mgmt"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Property Management team."

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
    log_file_path = log_dir / "team_property_manager_run.log"
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
def create_property_management_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Real-time AI Property Management' team."""
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Property Manager", role="Coordinator",
        description="Receives landlord requests and creates an operational plan for the specialist team.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader, file_writer, SendMessageTo()],
        workspace=workspace
    )
    maintenance_config = AgentConfig(
        name="Maintenance Coordinator", role="Operations",
        description="Triages maintenance requests, finds contractors, and coordinates repairs with tenants via the Communications Officer.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["maintenance_coordinator"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), GoogleSearch(), file_writer, SendMessageTo()],
        workspace=workspace,
    )
    communications_config = AgentConfig(
        name="Communications Officer", role="Communications",
        description="Handles all communication with tenants, acting only on instructions from other team members.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["communications_officer"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), send_tenant_notification],
        workspace=workspace,
    )
    financial_config = AgentConfig(
        name="Financial Clerk", role="Finance",
        description="Manages financial tasks like rent collection, instructing the Communications Officer to send reminders.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["financial_clerk"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_writer, SendMessageTo()],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="PropertyManagerTeam", description="An AI team to automate property management operations.")
        .set_coordinator(coordinator_config)
        .add_agent_node(maintenance_config)
        .add_agent_node(communications_config)
        .add_agent_node(financial_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'AI Property Management' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_property_management_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Real-time AI Property Management team.",
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
        default="./property_management_workspace",
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