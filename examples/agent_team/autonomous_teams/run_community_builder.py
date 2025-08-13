import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
import json
import re
from collections import Counter

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


# --- Embedded Prompts for the Community Builder Team ---
PROMPTS = {
    "coordinator": """You are the Community Manager, the coordinator of an AI team that helps an online creator build their community.
Your role is to receive a high-level goal from the creator, create a plan for your specialist agents, and synthesize their findings into a final report.

### Your Team
You have a team of autonomous specialists for data analysis, content strategy, and moderation.
{{team}}

### Your Workflow
1.  **Analyze Request**: The creator will ask you to analyze their community for a given period (e.g., "Analyze this week's community engagement").
2.  **Create a Plan**: Create a plan for your team. The plan MUST follow this sequence:
    1.  The `Engagement Analyst` and `Community Moderator` run first, in parallel.
    2.  The `Content Strategist` must run *after* the `Engagement Analyst` is complete.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will handle agent notifications.
4.  **Synthesize Report**: After the `Content Strategist` and `Community Moderator` have completed their tasks, read their reports (`engagement_report.json`, `moderation_report.md`, `discussion_topics.md`).
5.  **Final Output**: Create a single, consolidated report for the creator named `community_weekly_report.md`. Summarize the key insights, identify super-fans, list moderation actions, and suggest new discussion topics. Then, notify the user that the report is ready.

### Your Tools
{{tools}}
""",
    "engagement_analyst": """You are an Engagement Analyst. You identify key community members and popular topics from raw chat data.
When notified, you MUST use `GetTaskBoardStatus` to confirm your assignment.
1.  **Analyze**: Use the `analyze_chat_logs` tool with the `analysis_mode` set to 'engagement' on the provided mock data file (`mock_chat_log.txt`).
2.  **Report**: Save the structured JSON output from the tool to a new file named `engagement_report.json` using the `FileWriter` tool.
3.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "content_strategist": """You are a Content Strategist. You generate engaging discussion topics based on community data.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Data**: You MUST use the `FileReader` tool to read the `engagement_report.json` file produced by the Engagement Analyst.
2.  **Generate Topics**: Based on the identified popular keywords and super-fans, generate 3-5 new, engaging discussion questions or topics to foster more conversation.
3.  **Report**: Save your suggestions to a markdown file named `discussion_topics.md` using `FileWriter`.
4.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "community_moderator": """You are a Community Moderator. Your job is to keep the community safe and healthy by identifying rule violations.
When notified, use `GetTaskBoardStatus` to get your assignment.
1.  **Analyze**: Use the `analyze_chat_logs` tool with the `analysis_mode` set to 'moderation' on the provided mock data file (`mock_chat_log.txt`).
2.  **Report**: Create a markdown report of your findings named `moderation_report.md`. List each potential violation, the user who posted it, and a recommended action (e.g., Warn, Delete Message, Mute).
3.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.
4.  **Notify Coordinator**: You MUST use `SendMessageTo` to notify the `Community Manager` that your moderation scan is complete.

Your tools:
{{tools}}
"""
}


# --- Custom Tool for the Team (Simulating Community Analysis) ---
@tool(
    name="analyze_chat_logs",
    description="Analyzes a mock chat log file for either engagement metrics or moderation issues."
)
def analyze_chat_logs(context: AgentContextType, chat_log_path: str, analysis_mode: str) -> str:
    """
    Simulates analyzing a community chat log.
    In a real app, this would connect to Discord/YouTube APIs.
    """
    full_path = os.path.join(context.workspace.get_base_path(), chat_log_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Mock chat log file not found at {full_path}"})

    with open(full_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if analysis_mode == 'engagement':
        user_posts = Counter()
        keywords = Counter()
        stop_words = {'the', 'a', 'in', 'is', 'to', 'and', 'i', 'it', 'for', 'on'}
        for line in lines:
            match = re.match(r"\[(.+?)\]", line)
            if match:
                user = match.group(1)
                user_posts[user] += 1
                message_text = line.split(":", 1)[-1].strip().lower()
                words = re.findall(r'\b\w+\b', message_text)
                for word in words:
                    if word not in stop_words and not word.isdigit():
                        keywords[word] += 1
        
        super_fans = [user for user, count in user_posts.most_common(3)]
        popular_topics = [topic for topic, count in keywords.most_common(5)]

        result = {
            "super_fans": super_fans,
            "popular_topics": popular_topics,
            "total_messages": len(lines),
            "total_participants": len(user_posts)
        }
        return json.dumps(result, indent=2)

    elif analysis_mode == 'moderation':
        violations = []
        spam_phrases = ["my new project", "check out my site"]
        toxic_words = ["idiot", "stupid"]
        for i, line in enumerate(lines, 1):
            match = re.match(r"\[(.+?)\]:\s*(.*)", line)
            if not match:
                continue
            user, message = match.groups()

            for phrase in spam_phrases:
                if phrase in message.lower():
                    violations.append({
                        "line": i,
                        "user": user,
                        "message": message.strip(),
                        "violation_type": "Potential Spam",
                        "recommended_action": "Review and Delete Message"
                    })
            for word in toxic_words:
                if re.search(fr'\b{word}\b', message.lower()):
                    violations.append({
                        "line": i,
                        "user": user,
                        "message": message.strip(),
                        "violation_type": "Potential Toxicity",
                        "recommended_action": "Warn User"
                    })
        return json.dumps(violations, indent=2)
    else:
        return json.dumps({"error": f"Invalid analysis_mode: '{analysis_mode}'. Must be 'engagement' or 'moderation'."})


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
        return "simple_local_workspace_for_community"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Community Builder team."

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
    log_file_path = log_dir / "team_community_builder_run.log"
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
def create_community_builder_team(llm_model: str, workspace: BaseAgentWorkspace):
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Community Manager", role="Coordinator",
        description="Manages the community analysis and content strategy workflow.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader, file_writer],
        workspace=workspace
    )
    engagement_analyst_config = AgentConfig(
        name="Engagement Analyst", role="Analyst",
        description="Identifies super-fans and popular topics from community chat logs.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["engagement_analyst"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), analyze_chat_logs, file_writer],
        workspace=workspace
    )
    content_strategist_config = AgentConfig(
        name="Content Strategist", role="Strategist",
        description="Generates new discussion topics based on engagement data.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["content_strategist"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer],
        workspace=workspace
    )
    moderator_config = AgentConfig(
        name="Community Moderator", role="Moderator",
        description="Scans chat logs for rule violations and produces a moderation report.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["community_moderator"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), analyze_chat_logs, file_writer, SendMessageTo],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="CommunityBuilderTeam", description="An AI team to automate community management for online creators.")
        .set_coordinator(coordinator_config)
        .add_agent_node(engagement_analyst_config)
        .add_agent_node(content_strategist_config)
        .add_agent_node(moderator_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'AI Community Builder' team...")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace is set to: {workspace_path}")

    # Pre-populate the workspace with a mock chat log file for the simulation
    mock_chat_path = workspace_path / "mock_chat_log.txt"
    if not mock_chat_path.exists():
        with open(mock_chat_path, "w", encoding="utf-8") as f:
            f.write("[Alice]: I love the new feature! The UI is so much cleaner.\n")
            f.write("[Bob]: Totally agree with Alice. It makes finding things so much easier.\n")
            f.write("[Charlie]: Has anyone tried integrating it with the new API? I'm having some trouble.\n")
            f.write("[Alice]: @Charlie I got the API working. The trick is in the authentication header.\n")
            f.write("[David]: Check out my new project at spam-link.com, it's amazing!\n")
            f.write("[Bob]: The API documentation could be a bit clearer on the auth part.\n")
            f.write("[Eve]: You're an idiot, Charlie. It's obvious.\n")
            f.write("[Alice]: Hey, let's be supportive. We're all learning!\n")
        print(f"--> Mock data file created: {mock_chat_path}")

    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_community_builder_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the AI-powered Community Builder for Online Creators team.",
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
        default="./community_builder_workspace",
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