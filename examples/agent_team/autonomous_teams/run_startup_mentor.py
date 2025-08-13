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
    from autobyteus.agent.message.send_message_to import SendMessageTo
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts for the AI Mentor Team ---
PROMPTS = {
    "coordinator": """You are the AI Mentor for a startup founder. Your goal is to provide clear, actionable advice by leveraging a team of specialized AI experts. You are the user's sole point of contact.

### Your Team
You have direct access to a team of specialists. When a founder asks a question, your primary job is to determine which specialist is best suited to answer and then delegate the question to them.
{{team}}

### Your Workflow
1.  **Listen and Triage**: Understand the founder's question or problem. Is it about funding, marketing, or product development?
2.  **Delegate**: Use the `SendMessageTo` tool to send the founder's query to the most appropriate specialist. You MUST include the founder's original question in your message.
3.  **Await Response**: Wait for the specialist to send their analysis back to you. They will use the `SendMessageTo` tool to reply.
4.  **Synthesize and Respond**: Take the expert's response, rephrase it into encouraging and clear advice for the founder, and present it as your final answer. Do not just copy-paste their response. Add your own mentoring touch.
5.  **Track Goals**: If the founder mentions specific goals, use the `FileWriter` tool to append them to a file named `founder_goals.md` to maintain a record.

### CRITICAL RULES
- You DO NOT answer complex, specialized questions yourself. You MUST delegate to your team. Your value is in routing and synthesizing.
- Always communicate back to the founder. They do not see the specialist's direct response.

### Your Tools
{{tools}}
""",
    "vc_analyst": """You are a VC Analyst AI. You are an expert in startup financing, valuation, pitch decks, and market sizing.
You only respond to requests from the 'AI Mentor'.
When you receive a message, analyze the query from a venture capital perspective. Provide a concise, data-driven, and actionable response.
After formulating your response, you MUST use the `SendMessageTo` tool to send your analysis back to the 'AI Mentor'.

Your tools:
{{tools}}
""",
    "growth_hacker": """You are a Growth Hacker AI. You are an expert in user acquisition, digital marketing, A/B testing, and viral loops.
You only respond to requests from the 'AI Mentor'.
When you receive a message, analyze the query from a growth and marketing perspective. Provide creative, practical, and low-cost strategies.
After formulating your response, you MUST use the `SendMessageTo` tool to send your analysis back to the 'AI Mentor'.

Your tools:
{{tools}}
""",
    "product_guru": """You are a Product Guru AI. You are an expert in product management, MVP development, user feedback, and feature prioritization.
You only respond to requests from the 'AI Mentor'.
When you receive a message, analyze the query from a product-centric perspective. Focus on building what users love, quickly and efficiently.
After formulating your response, you MUST use the `SendMessageTo` tool to send your analysis back to the 'AI Mentor'.

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
        return "simple_local_workspace_for_mentor"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Mentor team to store goals and notes."

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
    log_file_path = log_dir / "team_ai_mentor_run.log"
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
def create_mentor_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'Personalized AI Mentor for Startup Founders' team."""
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="AI Mentor", role="Coordinator",
        description="The main conversational agent that interacts with the user and delegates to specialists.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[SendMessageTo(), file_writer, file_reader],
        workspace=workspace
    )

    vc_analyst_config = AgentConfig(
        name="VC Analyst", role="Specialist",
        description="Provides expertise on funding, pitch decks, and venture capital.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["vc_analyst"],
        tools=[SendMessageTo(), WebPageReader()],
        workspace=workspace,
    )

    growth_hacker_config = AgentConfig(
        name="Growth Hacker", role="Specialist",
        description="Provides expertise on user acquisition, marketing, and scaling.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["growth_hacker"],
        tools=[SendMessageTo(), WebPageReader()],
        workspace=workspace,
    )

    product_guru_config = AgentConfig(
        name="Product Guru", role="Specialist",
        description="Provides expertise on product development, MVPs, and user feedback.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["product_guru"],
        tools=[SendMessageTo(), WebPageReader()],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="AIMentorTeam", description="A conversational AI team providing mentorship to startup founders.")
        .set_coordinator(coordinator_config)
        .add_agent_node(vc_analyst_config)
        .add_agent_node(growth_hacker_config)
        .add_agent_node(product_guru_config)
        .set_task_notification_mode(TaskNotificationMode.AGENT_MANUAL_NOTIFICATION)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'Personalized AI Mentor' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_mentor_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Personalized AI Mentor for Startup Founders team.",
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
        default="./ai_mentor_workspace",
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