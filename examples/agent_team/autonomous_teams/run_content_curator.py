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
    from autobyteus.tools.browser.standalone.google_search_ui import GoogleSearch
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


# --- Embedded Prompts for the Content Curator Team ---
PROMPTS = {
    "coordinator": """You are the Newsletter Editor, the coordinator of a content curation team.
Your mission is to take a topic from the user and orchestrate your team to find the best content on the web and draft a newsletter issue.

### Your Team
You have a team of autonomous scouts and a writer.
{{team}}

### Your Workflow
1.  **Analyze Request**: The user will give you a topic (e.g., "advances in AI chip design").
2.  **Create a Plan**: Create a plan for your team. The plan MUST follow this sequence:
    1.  `Web Scout` and `Community Scout` run first, in parallel, to find relevant links.
    2.  `Content Synthesizer` runs *after* both scouts have completed their tasks.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will handle notifying the agents.
4.  **Final Review**: Once the `Content Synthesizer` completes the draft, your job is to present the final `draft_newsletter.md` file path to the user as the final result.

### Your Tools
{{tools}}
""",
    "web_scout": """You are a Web Scout. You find high-quality articles, blog posts, and academic papers.
When you are notified of a task, you MUST first use `GetTaskBoardStatus` to understand the topic you need to research.
1.  **Search**: Use the `GoogleSearch` tool to find relevant content. Use advanced search queries (e.g., `site:arxiv.org "LLM optimization"`, `"generative ai" blog post`).
2.  **Curate**: Identify the top 3-5 most insightful and recent links.
3.  **Report**: Write your findings to a file named `web_scout_report.md`. For each link, provide the URL and a one-sentence summary of why it's relevant.
4.  **Complete Task**: Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "community_scout": """You are a Community Scout. You find what practitioners and enthusiasts are talking about on social media and forums.
When you are notified of a task, you MUST first use `GetTaskBoardStatus` to understand the topic.
1.  **Search**: Use the `GoogleSearch` tool to search sites like X (Twitter), Hacker News, and relevant subreddits. Use queries like `site:twitter.com "AI in drug discovery"`, `site:news.ycombinator.com "geohot"`, `site:reddit.com/r/machinelearning "new models"`.
2.  **Curate**: Find the top 2-3 trending discussions, projects, or insightful comments.
3.  **Report**: Write your findings to a file named `community_scout_report.md`. For each link, provide the URL and a one-sentence summary of the discussion.
4.  **Complete Task**: Finally, use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "content_synthesizer": """You are a Content Synthesizer. You turn a list of links into a compelling newsletter draft.
When you are notified of a task, use `GetTaskBoardStatus` to get your assignment.
1.  **Read Reports**: You MUST use the `FileReader` tool to read both `web_scout_report.md` and `community_scout_report.md`.
2.  **Read Content**: For each URL in the reports, use the `WebPageReader` tool to get the full content of the article or discussion.
3.  **Summarize**: Write a concise, engaging summary (2-4 sentences) for each link.
4.  **Draft Newsletter**: Assemble these summaries into a markdown file named `draft_newsletter.md`. The draft should be well-structured with clear headings for each link.
5.  **Complete Task**: Finally, use `UpdateTaskStatus` to mark your task as 'completed'. The Editor will handle the final review.

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
        return "simple_local_workspace_for_curator"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Content Curator team."

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
    log_file_path = log_dir / "team_content_curator_run.log"
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
def create_content_curator_team(llm_model: str, workspace: BaseAgentWorkspace):
    """Creates the 'AI Content Curator for Tech Newsletters' team."""
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Newsletter Editor", role="Coordinator",
        description="Manages the content curation workflow from topic to final draft.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus()],
        workspace=workspace
    )

    web_scout_config = AgentConfig(
        name="Web Scout", role="Researcher",
        description="Scours blogs, news sites, and academic sources for relevant content.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["web_scout"],
        tools=[GoogleSearch(), file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )

    community_scout_config = AgentConfig(
        name="Community Scout", role="Researcher",
        description="Scours social media and forums like X, Hacker News, and Reddit.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["community_scout"],
        tools=[GoogleSearch(), file_writer, UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace,
    )

    synthesizer_config = AgentConfig(
        name="Content Synthesizer", role="Writer",
        description="Reads curated links, summarizes them, and drafts the newsletter.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["content_synthesizer"],
        tools=[file_reader, file_writer, WebPageReader(), UpdateTaskStatus(), GetTaskBoardStatus()],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="ContentCuratorTeam", description="An AI team that automates content discovery and newsletter drafting.")
        .set_coordinator(coordinator_config)
        .add_agent_node(web_scout_config)
        .add_agent_node(community_scout_config)
        .add_agent_node(synthesizer_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'AI Content Curator' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_content_curator_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the AI Content Curator for Tech Newsletters team.",
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
        default="./content_curator_workspace",
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