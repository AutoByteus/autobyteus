import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
import json

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


# --- Embedded Prompts for the Carbon Footprint Tracker Team ---
PROMPTS = {
    "coordinator": """You are a Sustainability Coach, the coordinator of an AI team that helps users track their carbon footprint.
Your job is to receive a user's request to analyze their data, and then create a plan for your specialist team to execute.

### Your Team
You command a team of data-gathering and analysis agents.
{{team}}

### Your Workflow
1.  **Analyze Request**: The user will ask you to analyze their footprint.
2.  **Create a Plan**: Create a plan for your team. The plan MUST follow this sequence:
    1.  The `Email Scanner`, `Calendar Analyst`, and `Location Analyst` must run first. They can run in parallel (no dependencies).
    2.  The `Carbon Calculator` must run *after* all three data-gathering agents are complete.
    3.  The `Lifestyle Advisor` must run *after* the `Carbon Calculator` is complete.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will handle agent notifications.
4.  **Final Report**: After the `Lifestyle Advisor` notifies you of completion, read their report (`reduction_tips.md`) and the `carbon_footprint_report.json`, then present a final, encouraging summary to the user.

### Your Tools
{{tools}}
""",
    "email_scanner": """You are an Email Scanner AI. You specialize in finding and extracting carbon-relevant data from email receipts.
When you are notified of a task, use `GetTaskBoardStatus` to confirm your assignment.
1.  **Scan**: Use the `scan_email_for_receipts` tool on the provided mock data file (`mock_emails.txt`).
2.  **Report**: Save the structured JSON output from the tool to a new file named `email_data.json` using the `FileWriter` tool.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "calendar_analyst": """You are a Calendar Analyst AI. You identify travel-related events from calendar data.
When notified, use `GetTaskBoardStatus` to confirm your task.
1.  **Scan**: Use the `scan_calendar_for_travel` tool on the provided mock data file (`mock_calendar.txt`).
2.  **Report**: Save the tool's JSON output to a new file named `calendar_data.json` using the `FileWriter` tool.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "location_analyst": """You are a Location Analyst AI. You infer travel patterns from raw location data.
When notified, use `GetTaskBoardStatus` to confirm your task.
1.  **Analyze**: Use the `analyze_location_data` tool on the provided mock data file (`mock_gps_log.csv`).
2.  **Report**: Save the tool's JSON output to a new file named `location_data.json` using the `FileWriter` tool.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "carbon_calculator": """You are a Carbon Calculator AI. You are an expert at converting activities into CO2 equivalent emissions.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Data**: You MUST use `FileReader` to read `email_data.json`, `calendar_data.json`, and `location_data.json`.
2.  **Calculate**: For each activity found in the files, use the `calculate_carbon_emissions` tool to get the carbon footprint.
3.  **Report**: Aggregate all the results into a final report. Save this report as `carbon_footprint_report.json` using the `FileWriter` tool.
4.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "lifestyle_advisor": """You are a Lifestyle Advisor AI. You provide personalized, actionable tips for reducing one's carbon footprint.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Analyze Report**: You MUST use `FileReader` to read the `carbon_footprint_report.json`.
2.  **Generate Tips**: Identify the largest sources of emissions from the report and generate 3-5 practical, personalized tips for the user to reduce their impact.
3.  **Write Report**: Save your tips to a markdown file named `reduction_tips.md` using `FileWriter`.
4.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.
5.  **Notify Coordinator**: Finally, you MUST use `SendMessageTo` to send a message to the 'Sustainability Coach' that the final report is ready.

Your tools:
{{tools}}
"""
}


# --- Custom Tools for the Team (Simulating Data Integrations) ---
@tool(name="scan_email_for_receipts")
def scan_email_for_receipts(context: AgentContextType, email_file_path: str) -> str:
    """Simulates scanning an email inbox file for receipts and returns a JSON list of found items."""
    logging.info(f"Tool 'scan_email_for_receipts' reading from {email_file_path}")
    # In a real app, this would use Gmail API, etc. Here we read a mock file.
    full_path = os.path.join(context.workspace.get_base_path(), email_file_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Mock email file not found at {full_path}"})
    
    # Mock analysis
    results = [
        {"type": "flight", "details": {"from": "SFO", "to": "JFK", "class": "economy"}},
        {"type": "purchase", "details": {"vendor": "Amazon", "category": "electronics", "amount_usd": 78.50}},
        {"type": "ground_travel", "details": {"service": "Uber", "distance_miles": 12.5}}
    ]
    return json.dumps(results, indent=2)

@tool(name="scan_calendar_for_travel")
def scan_calendar_for_travel(context: AgentContextType, calendar_file_path: str) -> str:
    """Simulates scanning a calendar file for travel events."""
    logging.info(f"Tool 'scan_calendar_for_travel' reading from {calendar_file_path}")
    full_path = os.path.join(context.workspace.get_base_path(), calendar_file_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Mock calendar file not found at {full_path}"})
        
    results = [
        {"type": "flight", "details": {"from": "LHR", "to": "DXB", "class": "business"}}
    ]
    return json.dumps(results, indent=2)

@tool(name="analyze_location_data")
def analyze_location_data(context: AgentContextType, gps_log_path: str) -> str:
    """Simulates analyzing a GPS log to infer travel."""
    logging.info(f"Tool 'analyze_location_data' reading from {gps_log_path}")
    full_path = os.path.join(context.workspace.get_base_path(), gps_log_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Mock GPS file not found at {full_path}"})

    results = [
        {"type": "ground_travel", "details": {"service": "personal_car_gas", "distance_miles": 150.0}}
    ]
    return json.dumps(results, indent=2)

@tool(name="calculate_carbon_emissions")
def calculate_carbon_emissions(context: AgentContextType, activity_type: str, details: dict) -> str:
    """Simulates calculating CO2e for a given activity using emission factors."""
    # Emission factors in kgCO2e per unit (highly simplified for demo)
    EMISSION_FACTORS = {
        "flight": {"economy": 0.15, "business": 0.45}, # per passenger-mile
        "purchase": {"electronics": 0.5, "clothing": 0.2, "groceries": 0.1}, # per USD
        "ground_travel": {"Uber": 0.25, "personal_car_gas": 0.4}, # per mile
    }
    # Simplified distance estimates for flights (miles)
    FLIGHT_DISTANCES = {
        ("SFO", "JFK"): 2586,
        ("LHR", "DXB"): 3421,
    }

    footprint = 0.0
    calculation_note = "Factor not found"
    
    if activity_type == "flight":
        route = (details.get("from"), details.get("to"))
        distance = FLIGHT_DISTANCES.get(route, 0)
        factor = EMISSION_FACTORS.get("flight", {}).get(details.get("class", "economy"), 0)
        footprint = distance * factor
        calculation_note = f"{distance} miles * {factor} kgCO2e/mile"
    elif activity_type == "purchase":
        factor = EMISSION_FACTORS.get("purchase", {}).get(details.get("category"), 0)
        amount = details.get("amount_usd", 0)
        footprint = amount * factor
        calculation_note = f"${amount} * {factor} kgCO2e/$"
    elif activity_type == "ground_travel":
        factor = EMISSION_FACTORS.get("ground_travel", {}).get(details.get("service"), 0)
        distance = details.get("distance_miles", 0)
        footprint = distance * factor
        calculation_note = f"{distance} miles * {factor} kgCO2e/mile"

    result = {
        "activity": activity_type,
        "details": details,
        "footprint_kgCO2e": round(footprint, 2),
        "calculation_note": calculation_note
    }
    return json.dumps(result)


# --- Core Components ---
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
        return "simple_local_workspace_for_carbon_tracker"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the Carbon Footprint Tracker team."

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
    log_dir = Path(sys.path[0]) / "logs" if "autobyteus" in sys.path[0] else Path("./logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "team_carbon_tracker_run.log"
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
            for model in all_models:
                print(f"  - {model.model_identifier}")
        except Exception as e:
            print(f"Additionally, an error occurred while listing models: {e}", file=sys.stderr)
        sys.exit(1)


# --- Team Factory Function ---
def create_carbon_footprint_team(llm_model: str, workspace: BaseAgentWorkspace):
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Sustainability Coach", role="Coordinator",
        description="Manages the carbon footprint analysis workflow.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader],
        workspace=workspace
    )
    email_scanner_config = AgentConfig(
        name="Email Scanner", role="Data Collector",
        description="Scans emails for carbon-relevant receipts.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["email_scanner"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), scan_email_for_receipts, file_writer],
        workspace=workspace
    )
    calendar_analyst_config = AgentConfig(
        name="Calendar Analyst", role="Data Collector",
        description="Scans calendars for travel events.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["calendar_analyst"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), scan_calendar_for_travel, file_writer],
        workspace=workspace
    )
    location_analyst_config = AgentConfig(
        name="Location Analyst", role="Data Collector",
        description="Analyzes GPS logs to infer travel.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["location_analyst"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), analyze_location_data, file_writer],
        workspace=workspace
    )
    carbon_calculator_config = AgentConfig(
        name="Carbon Calculator", role="Analyst",
        description="Calculates CO2e emissions based on collected activity data.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["carbon_calculator"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer, calculate_carbon_emissions],
        workspace=workspace
    )
    lifestyle_advisor_config = AgentConfig(
        name="Lifestyle Advisor", role="Advisor",
        description="Generates personalized tips for carbon footprint reduction.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["lifestyle_advisor"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer, SendMessageTo],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="CarbonTrackerTeam", description="An AI team to automate personal carbon footprint tracking and provide advice.")
        .set_coordinator(coordinator_config)
        .add_agent_node(email_scanner_config)
        .add_agent_node(calendar_analyst_config)
        .add_agent_node(location_analyst_config)
        .add_agent_node(carbon_calculator_config)
        .add_agent_node(lifestyle_advisor_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'Personal Carbon Footprint Tracker' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")

    # Pre-populate the workspace with mock data files for the simulation
    mock_data = {
        "mock_emails.txt": "From: United Airlines <confirm@united.com>\nSubject: Your flight to New York is confirmed\nDetails: SFO to JFK, Economy class.\n\nFrom: Amazon <orders@amazon.com>\nSubject: Your order of 'Bose Headphones' has shipped\nTotal: $78.50, Category: electronics\n\nFrom: Uber <receipts@uber.com>\nSubject: Your Wednesday trip\nDistance: 12.5 miles",
        "mock_calendar.txt": "EVENT: Flight to Dubai\nDATE: 2023-11-15\nDETAILS: LHR to DXB, Business Class",
        "mock_gps_log.csv": "timestamp,latitude,longitude\n1672531200,34.0522,-118.2437\n1672534800,36.1699,-115.1398"
    }
    for filename, content in mock_data.items():
        path = workspace_path / filename
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"--> Mock data file created: {path}")

    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_carbon_footprint_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the AI Personal Carbon Footprint Tracker team.",
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
        default="./carbon_tracker_workspace",
        help="Directory for the shared agent workspace, containing mock data files."
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