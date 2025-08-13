
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
    from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
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


# --- Embedded Prompts for the E-commerce Optimizer Team ---
PROMPTS = {
    "coordinator": """You are the E-commerce Strategist, the coordinator of the Optimizer team.
Your mission is to take a user's request, which includes their store URL and product niche, and generate a comprehensive optimization plan.

### Your Team
You command a team of specialists to gather and analyze data.
{{team}}

### Your Workflow
1.  **Analyze and Plan**: Based on the user's request, create a sequential plan for your team. The plan MUST follow this order:
    1.  `Market Researcher` and `Data Analyst` should run first. They can run in parallel (no dependencies on each other).
    2.  `SEO Specialist` must run *after* both the Market Researcher and Data Analyst are complete.
    3.  `Pricing Specialist` must also run *after* both the Market Researcher and Data Analyst are complete.
2.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will handle notifying agents as dependencies are met.
3.  **Synthesize Report**: After your specialists complete their work, you will receive a notification from the Pricing Specialist. Then, read all the generated report files (`market_research.md`, `store_data_analysis.json`, `seo_recommendations.csv`, `pricing_recommendations.csv`).
4.  **Final Output**: Create a final, consolidated report for the user named `final_optimization_report.md` summarizing all findings and recommendations.

### Your Tools
{{tools}}
""",
    "market_researcher": """You are a Market Researcher. Your focus is on understanding the competitive landscape for a specific e-commerce niche.
When you receive a task, use `GetTaskBoardStatus` to understand your assignment.
Your job is to use your web reading capabilities to find top competitors, analyze their product listings, identify common keywords, and report on pricing trends.
You MUST write your findings to a markdown file named `market_research.md` using the `FileWriter` tool.
Finally, and most importantly, use `UpdateTaskStatus` to mark your task as 'completed'. The system will notify the next agents.

Here are your tools:
{{tools}}
""",
    "data_analyst": """You are a Data Analyst. You extract and interpret data directly from the client's e-commerce store.
When you receive a task, use `GetTaskBoardStatus` to find your assigned store URL.
Your job is to "scrape" the product pages to collect data like product titles, descriptions, and prices.
Then, perform a basic analysis of this data. For example, what is the average price, what are the most common words in descriptions?
You MUST save both the raw data and your analysis into a single JSON file named `store_data_analysis.json` using the `FileWriter` tool.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Here are your tools:
{{tools}}
""",
    "seo_specialist": """You are an SEO Specialist. You craft product copy that ranks high and converts customers.
When you are notified of a task, first use `GetTaskBoardStatus` to get the details.
Your task is to generate optimized product titles and descriptions. To do this, you MUST first read the findings from `market_research.md` and `store_data_analysis.json` using the `FileReader` tool.
Based on the market trends and existing store data, create a list of new, SEO-friendly titles and descriptions.
Format your output as a CSV and save it to `seo_recommendations.csv` using the `FileWriter` tool. The CSV should have columns: `product_name`, `recommended_title`, `recommended_description`.
Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "pricing_specialist": """You are a Pricing Specialist. Your goal is to maximize profit by finding the optimal price point.
When you are notified of a task, first use `GetTaskBoardStatus` to get the details.
You MUST read the `market_research.md` and `store_data_analysis.json` files using the `FileReader` tool.
Analyze competitor pricing and the client's current prices. Recommend new prices for each product, providing a brief justification for each change.
Format your recommendations as a CSV and save it to `pricing_recommendations.csv` using `FileWriter`. The CSV should have columns: `product_name`, `current_price`, `recommended_price`, `justification`.
After updating your task status to 'completed' with `UpdateTaskStatus`, you MUST send a final notification to the 'ECommerce Strategist' using the `SendMessageTo` tool to inform them that all analysis is complete.

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
        return "simple_local_workspace_for_ecommerce"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the e-commerce optimization team."

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
    log_file_path = log_dir / "team_ecommerce_optimizer_run.log"
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
def create_ecommerce_optimizer_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'AI-driven Niche E-commerce Optimizer' team."""
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="ECommerce Strategist", role="Coordinator",
        description="Takes a user request (store URL, niche) and creates a detailed, sequential plan for the specialist team.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader, file_writer],
        workspace=workspace
    )
    market_researcher_config = AgentConfig(
        name="Market Researcher", role="Analyst",
        description="Researches competitors, keywords, and pricing trends for a given e-commerce niche.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["market_researcher"],
        tools=[WebPageReader(), file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )
    data_analyst_config = AgentConfig(
        name="Data Analyst", role="Analyst",
        description="Scrapes and analyzes product data from the user's e-commerce store.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["data_analyst"],
        tools=[WebPageReader(), file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )
    seo_specialist_config = AgentConfig(
        name="SEO Specialist", role="Content Creator",
        description="Generates optimized product titles and descriptions based on market and store data.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["seo_specialist"],
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )
    pricing_specialist_config = AgentConfig(
        name="Pricing Specialist", role="Analyst",
        description="Recommends optimal product pricing based on market and store data.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["pricing_specialist"],
        tools=[file_reader, file_writer, UpdateTaskStatus(), GetTaskBoardStatus(), SendMessageTo()],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="ECommerceOptimizerTeam", description="An AI team to provide actionable e-commerce optimizations.")
        .set_coordinator(coordinator_config)
        .add_agent_node(market_researcher_config)
        .add_agent_node(data_analyst_config)
        .add_agent_node(seo_specialist_config)
        .add_agent_node(pricing_specialist_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'E-commerce Optimizer' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_ecommerce_optimizer_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the AI-driven Niche E-commerce Optimizer team.",
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
        default="./ecommerce_optimizer_workspace",
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