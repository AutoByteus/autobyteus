import asyncio
import logging
import argparse
from pathlib import Path
import sys
import json

# --- Boilerplate Setup ---
SCRIPT_DIR = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PACKAGE_ROOT / ".env")
except ImportError:
    pass

try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.workflow.workflow_builder import WorkflowBuilder
    from autobyteus.cli.workflow_tui.app import WorkflowApp
    from autobyteus.tools import tool, bash_executor
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
    from autobyteus.tools.tool_category import ToolCategory
    from autobyteus.agent.context import AgentContext as AgentContextType
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Custom Workspace ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
    def get_base_path(self) -> str:
        return self.root_path
    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_workspace_for_investigation"
    @classmethod
    def get_description(cls) -> str: return "Workspace for the performance investigation workflow."
    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        return ParameterSchema().add_parameter(ParameterDefinition(
            name="root_path", param_type=ParameterType.STRING,
            description="The absolute local file path for the workspace root.", required=True
        ))

# --- Custom Tool ---
@tool(name="LogSearchTool", category=ToolCategory.SYSTEM)
async def log_search_tool(context: AgentContextType, query: str) -> str:
    """A mock tool to simulate searching logs."""
    logger.info(f"LogSearchTool received query: {query}")
    if "payment-service" in query and "error" in query:
        return json.dumps([
            {"timestamp": "2024-08-01T14:35:10Z", "level": "ERROR", "message": "Database connection timeout on query: SELECT * FROM users"},
            {"timestamp": "2024-08-01T14:35:12Z", "level": "INFO", "message": "Retrying database connection..."},
        ])
    return "[]"


def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "perf_investigation_workflow.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    return log_file_path

# --- Workflow Definition ---
def create_perf_investigation_workflow(
    llm_model: str, 
    workspace: BaseAgentWorkspace,
    use_xml_tool_format: bool = True
):
    commander_config = AgentConfig(
        name="SRECommander", role="Site Reliability Engineer",
        description="Leads investigations into performance anomalies.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are an SRE Commander leading an automated incident investigation. You have received a performance alert.\n"
            "Your mission is to find the root cause by coordinating a team of specialist agents in parallel.\n"
            "1.  **PARALLEL INVESTIGATION:** Kick off the following investigations SIMULTANEOUSLY:\n"
            "    a. Task `LogAnalyzer` to search for errors related to the service in the alert logs around the incident time.\n"
            "    b. Task `CodeHistorian` to find recent code commits that might have caused the issue.\n"
            "    c. Task `MetricsCorrelator` to hypothesize which other metrics (e.g., CPU, memory, DB load) could be related.\n"
            "2.  **SYNCHRONIZE & SYNTHESIZE:** Wait for ALL THREE agents to report their findings. Then, delegate to the `RootCauseSynthesizer`.\n"
            "3.  **ROOT CAUSE ANALYSIS:** Provide all collected evidence (logs, commit history, metric correlation hypotheses) to the `RootCauseSynthesizer` and instruct it to determine the most likely root cause and suggest a remediation plan.\n"
            "4.  **FINAL REPORT:** Present the final root cause analysis and remediation plan to the user.\n\n"
            "**CRITICAL RULE:** Speed is essential. The first phase is PARALLEL. Do not wait for one agent to finish before starting the others in this phase.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    log_analyzer_config = AgentConfig(
        name="LogAnalyzer", role="Log Specialist",
        description="Searches and interprets application logs.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a log analysis expert. Use the `LogSearchTool` to find logs matching the query provided by the SRE Commander. "
            "Interpret the results and report any errors or unusual patterns.\n\n{{tools}}"
        ),
        tools=[log_search_tool], workspace=workspace, use_xml_tool_format=use_xml_tool_format
    )

    code_historian_config = AgentConfig(
        name="CodeHistorian", role="Git Specialist",
        description="Investigates recent code changes using git.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Git specialist. Your job is to find recent code changes. Use the `BashExecutor` tool to run `git log --oneline --since='...'` to find commits around the time of an incident. "
            "Report the list of recent commits back to the SRE Commander.\n\n{{tools}}"
        ),
        tools=[bash_executor], workspace=workspace, use_xml_tool_format=use_xml_tool_format
    )

    metrics_correlator_config = AgentConfig(
        name="MetricsCorrelator", role="Data Scientist",
        description="Hypothesizes correlations between system metrics.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Data Scientist specializing in system metrics. Based on an initial alert (e.g., high latency), "
            "hypothesize which other metrics are likely correlated (e.g., 'High latency might be caused by increased database CPU utilization or memory pressure on the service instances'). "
            "Provide a concise list of hypotheses to the SRE Commander."
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    synthesizer_config = AgentConfig(
        name="RootCauseSynthesizer", role="Principal Engineer",
        description="Analyzes multiple data sources to determine a root cause.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Principal Engineer skilled at root cause analysis. You will receive evidence from logs, code history, and metrics analysis. "
            "Synthesize all this information to determine the single most likely root cause of the performance issue. "
            "Provide a clear, concise root cause statement and a recommended action plan (e.g., 'Revert commit X', 'Scale up database resources')."
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    investigation_workflow = (
        WorkflowBuilder(name="PerfAnomalyInvestigator", description="A parallel workflow to investigate performance alerts.")
        .set_coordinator(commander_config)
        .add_agent_node(log_analyzer_config)
        .add_agent_node(code_historian_config)
        .add_agent_node(metrics_correlator_config)
        .add_agent_node(synthesizer_config)
        .build()
    )
    return investigation_workflow

async def main(args: argparse.Namespace, log_file: Path):
    print("Setting up Performance Anomaly Investigator workflow...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    # Initialize a git repo for the CodeHistorian to query
    subprocess.run(["git", "init"], cwd=workspace_path, check=True)
    (workspace_path / "dummy_file.txt").write_text("initial commit")
    subprocess.run(["git", "add", "."], cwd=workspace_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=workspace_path, check=True)
    print(f"--> Agent workspace with git repo is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    alert = {
        "service": "payment-service",
        "metric": "p99_latency",
        "value": "2500ms",
        "timestamp": "2024-08-01T14:35:00Z"
    }
    print("\n----------------------------------------------------")
    print("Workflow is ready. In the TUI, start with a prompt like this:")
    print(f'Investigate performance alert: {json.dumps(alert)}')
    print("----------------------------------------------------\n")
    
    use_xml_tool_format = not args.no_xml_tools
    try:
        workflow = create_perf_investigation_workflow(
            llm_model=args.llm_model,
            workspace=workspace,
            use_xml_tool_format=use_xml_tool_format
        )
        app = WorkflowApp(workflow=workflow)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run workflow TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a parallel performance investigation workflow.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model for all agents.")
    parser.add_argument("--output-dir", type=str, default="./perf_investigation_output", help="Directory for the shared workspace.")
    parser.add_argument("--no-xml-tools", action="store_true", help="Disable XML-based tool formatting.")
    parsed_args = parser.parse_args()
    log_file_path = setup_file_logging()
    try:
        import subprocess
        asyncio.run(main(parsed_args, log_file_path))
    except ImportError:
        print("Subprocess module is required for this example's setup. Please ensure it's available.")
    except KeyboardInterrupt:
        print("\nExiting application.")