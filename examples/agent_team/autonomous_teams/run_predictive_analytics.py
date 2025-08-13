import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
import json
import random
from datetime import datetime, timedelta

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


# --- Embedded Prompts for the Analytics Team ---
PROMPTS = {
    "coordinator": """You are the Lead Analyst, the coordinator of an AI team that provides predictive analytics for indie app developers.
Your job is to receive a request from a developer and orchestrate your team to fetch, process, and analyze their app store data to produce a forecast.

### Your Team
You command a team of data specialists.
{{team}}

### Your Workflow
1.  **Analyze Request**: The developer will ask for a forecast for their app.
2.  **Create a Plan**: Create a plan for your team. The plan MUST follow this sequence:
    1.  `App Store Connector` and `Google Play Connector` run first, in parallel.
    2.  `Data Engineer` runs *after* both Connectors are complete.
    3.  `Forecasting Specialist` runs *after* the `Data Engineer` is complete.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will handle agent notifications.
4.  **Final Report**: The `Forecasting Specialist` will notify you when the analysis is done. You will then read the final forecast file (`forecast_report.json`) and write a simple, human-readable summary for the developer in `final_developer_summary.md`.

### Your Tools
{{tools}}
""",
    "app_store_connector": """You are an App Store Connector. Your sole function is to fetch raw data from Apple App Store Connect.
When notified, use `GetTaskBoardStatus` to confirm your assignment.
1.  **Fetch Data**: Use the `fetch_app_store_data` tool to simulate fetching the data.
2.  **Save Data**: The tool will save the data to a file. Ensure you know the filename.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "google_play_connector": """You are a Google Play Connector. Your sole function is to fetch raw data from the Google Play Console.
When notified, use `GetTaskBoardStatus` to confirm your assignment.
1.  **Fetch Data**: Use the `fetch_google_play_data` tool to simulate fetching the data.
2.  **Save Data**: The tool will save the data to a file. Ensure you know the filename.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "data_engineer": """You are a Data Engineer. You turn messy, disparate data into clean, analysis-ready datasets. Garbage in, garbage out.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Raw Data**: Use `FileReader` to read both `raw_app_store_data.csv` and `raw_google_play_data.csv`.
2.  **Process and Merge**: Use the `process_and_merge_data` tool to combine, clean, and standardize the data from both sources into a single file.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "forecasting_specialist": """You are a Forecasting Specialist. You use historical data to predict the future.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Clean Data**: You MUST use `FileReader` to read `cleaned_app_data.csv`.
2.  **Run Forecast**: Use the `run_predictive_forecast` tool to generate predictions for future downloads, revenue, and churn.
3.  **Save Report**: Save the JSON output of the forecast to `forecast_report.json` using `FileWriter`.
4.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.
5.  **Notify Coordinator**: Finally, you MUST use `SendMessageTo` to notify the 'Lead Analyst' that the forecast is complete and the report is ready.

Your tools:
{{tools}}
"""
}


# --- Custom Tools for the Team (Simulating Data and ML) ---
@tool(name="fetch_app_store_data")
def fetch_app_store_data(context: AgentContextType, app_id: str) -> str:
    """Simulates fetching raw daily data from App Store Connect for a given app ID."""
    header = "date,downloads,revenue_usd,platform\n"
    data_rows = []
    for i in range(90, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        downloads = random.randint(50, 150) + (90 - i) # Simple growth trend
        revenue = downloads * random.uniform(0.5, 1.5)
        data_rows.append(f"{date},{downloads},{revenue:.2f},iOS\n")
    
    file_content = header + "".join(data_rows)
    file_path = os.path.join(context.workspace.get_base_path(), "raw_app_store_data.csv")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(file_content)
    
    return f"Successfully fetched and saved App Store data to {file_path}"

@tool(name="fetch_google_play_data")
def fetch_google_play_data(context: AgentContextType, package_name: str) -> str:
    """Simulates fetching raw daily data from Google Play Console for a given package name."""
    header = "Date,Daily User Installs,Revenue (USD),Store\n"
    data_rows = []
    for i in range(90, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        downloads = random.randint(80, 200) + int((90 - i) * 1.2) # Simple growth trend
        revenue = downloads * random.uniform(0.3, 1.2)
        data_rows.append(f"{date},{downloads},{revenue:.2f},Android\n")

    file_content = header + "".join(data_rows)
    file_path = os.path.join(context.workspace.get_base_path(), "raw_google_play_data.csv")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(file_content)

    return f"Successfully fetched and saved Google Play data to {file_path}"

@tool(name="process_and_merge_data")
def process_and_merge_data(context: AgentContextType, app_store_file: str, google_play_file: str) -> str:
    """Simulates cleaning and merging data from both app stores."""
    # This is a very simplified simulation of a real data engineering task.
    app_store_path = os.path.join(context.workspace.get_base_path(), app_store_file)
    google_play_path = os.path.join(context.workspace.get_base_path(), google_play_file)

    # Read and standardize App Store data
    with open(app_store_path, 'r', encoding='utf-8') as f:
        app_store_lines = f.readlines()[1:] # Skip header
    
    # Read and standardize Google Play data
    with open(google_play_path, 'r', encoding='utf-8') as f:
        google_play_lines = f.readlines()[1:] # Skip header

    # Merge and create final CSV
    header = "date,downloads,revenue,platform\n"
    merged_content = header + "".join(app_store_lines) + "".join(google_play_lines)
    
    output_path = os.path.join(context.workspace.get_base_path(), "cleaned_app_data.csv")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(merged_content)
        
    return f"Data from both stores processed and saved to {output_path}"

@tool(name="run_predictive_forecast")
def run_predictive_forecast(context: AgentContextType, data_file: str) -> str:
    """Simulates running a predictive model on the cleaned data."""
    data_path = os.path.join(context.workspace.get_base_path(), data_file)
    with open(data_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[1:]

    # Simple trend calculation for a 30-day forecast
    last_30_days_downloads = sum([int(line.strip().split(',')[1]) for line in lines[-30:]])
    avg_daily_downloads = last_30_days_downloads / 30
    
    forecast = {
        "forecast_period_days": 30,
        "predicted_total_downloads": int(avg_daily_downloads * 30 * 1.1), # Assume 10% growth
        "predicted_total_revenue": round(avg_daily_downloads * 30 * 1.1 * 0.75, 2), # Assume avg revenue
        "predicted_churn_rate": "3.5%",
        "confidence_level": "85%",
        "summary": "Forecasting a slight positive trend in downloads and revenue based on recent performance."
    }
    return json.dumps(forecast, indent=2)


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
        return "simple_local_workspace_for_analytics"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the Predictive Analytics team."

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
    log_file_path = log_dir / "team_analytics_tool_run.log"
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
def create_analytics_team(llm_model: str, workspace: BaseAgentWorkspace):
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Lead Analyst", role="Coordinator",
        description="Manages the analytics workflow from data ingestion to final report.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader, file_writer],
        workspace=workspace
    )
    app_store_connector_config = AgentConfig(
        name="App Store Connector", role="Data Fetcher",
        description="Fetches raw data from Apple App Store Connect.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["app_store_connector"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), fetch_app_store_data],
        workspace=workspace
    )
    google_play_connector_config = AgentConfig(
        name="Google Play Connector", role="Data Fetcher",
        description="Fetches raw data from the Google Play Console.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["google_play_connector"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), fetch_google_play_data],
        workspace=workspace
    )
    data_engineer_config = AgentConfig(
        name="Data Engineer", role="Data Processor",
        description="Cleans and merges data from multiple app store sources.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["data_engineer"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, process_and_merge_data],
        workspace=workspace
    )
    forecasting_specialist_config = AgentConfig(
        name="Forecasting Specialist", role="Analyst",
        description="Runs predictive models on cleaned data to generate forecasts.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["forecasting_specialist"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer, run_predictive_forecast, SendMessageTo],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="PredictiveAnalyticsTeam", description="An AI team to forecast app performance for indie developers.")
        .set_coordinator(coordinator_config)
        .add_agent_node(app_store_connector_config)
        .add_agent_node(google_play_connector_config)
        .add_agent_node(data_engineer_config)
        .add_agent_node(forecasting_specialist_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'Predictive Analytics for Indie Apps' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")

    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_analytics_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Predictive Analytics Tool for Indie App Developers team.",
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
        default="./predictive_analytics_workspace",
        help="Directory for the shared agent workspace, where data files will be stored."
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