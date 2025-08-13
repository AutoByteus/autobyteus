"""
VR-enhanced AI Therapy for Creative Blocks

This script defines and runs the "VR-enhanced AI Therapy for Creative Blocks" team using the AutoByteus framework.
The team is designed to provide therapeutic support for individuals experiencing creative blocks through a combination of voice analysis, cognitive strategies, and virtual reality environment changes.

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
import json
import re

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
    from autobyteus.agent.message.send_message_to import SendMessageTo
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
    from autobyteus.agent.context import AgentContext as AgentContextType
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts for the VR Therapy Team ---
PROMPTS = {
    "coordinator": """You are the AI Therapist, the primary point of contact for a creative individual experiencing a block. Your persona is empathetic, insightful, and calm.

Your core function is to facilitate a therapeutic session by orchestrating a team of specialists. You do not perform deep analysis yourself; you delegate and synthesize.

### Your Team
You have access to a team of specialized AI agents.
{{team}}

### Your Workflow
1.  **Listen**: The user will express their creative struggle.
2.  **Analyze Tone**: First, delegate the user's message to the `Vocal Analyst` using `SendMessageTo` to understand their emotional state.
3.  **Get Strategy**: Once the `Vocal Analyst` responds, delegate the user's problem AND their emotional state to the `Cognitive Specialist` using `SendMessageTo`.
4.  **Implement Environment**: When the `Cognitive Specialist` provides a therapeutic technique, delegate the technique's theme to the `Environment Weaver` using `SendMessageTo`.
5.  **Synthesize and Guide**: After the `Environment Weaver` confirms the change, synthesize the specialist's advice and the environment change into a single, cohesive response for the user. Guide them through the exercise.
6.  **Log Session**: Keep a brief log of the session in `session_notes.md` using `FileWriter`.

### CRITICAL RULES
- You must follow the workflow sequentially. Do not skip steps.
- Your final response to the user should be a synthesis. Do not just forward messages from specialists.

### Your Tools
{{tools}}
""",
    "vocal_analyst": """You are a Vocal Analyst AI. You are a dispassionate expert in detecting emotional states from text, simulating vocal tone analysis.
You only communicate with the 'AI Therapist'.
When you receive a message, your sole job is to use the `analyze_vocal_tone` tool on the provided text.
After getting the result, you MUST use `SendMessageTo` to send the JSON result back to the 'AI Therapist'.

Your tools:
{{tools}}
""",
    "cognitive_specialist": """You are a Cognitive Specialist AI. You are an expert in therapeutic techniques for overcoming creative blocks, such as CBT, narrative therapy, and divergent thinking exercises.
You only communicate with the 'AI Therapist'.
You will receive a user's problem and their emotional state. Based on this input, devise a single, simple, and actionable creative exercise.
Your response MUST include a 'technique_name' and a 'vr_environment_theme'.
Example response: "Technique: 'Object Association'. Ask the user to describe the object in front of them in the new environment using only verbs. VR Environment Theme: 'Minimalist Desert'."
You MUST use the `SendMessageTo` tool to send your recommended technique back to the 'AI Therapist'.

Your tools:
{{tools}}
""",
    "environment_weaver": """You are an Environment Weaver AI. You are the interface to the simulated VR engine.
You only communicate with the 'AI Therapist'.
You will receive a command to change the environment to a specific theme.
1.  Use the `set_vr_environment` tool to apply the change.
2.  You MUST use `SendMessageTo` to send a confirmation message (e.g., "Environment successfully changed to 'Minimalist Desert'") back to the 'AI Therapist'.

Your tools:
{{tools}}
"""
}


# --- Custom Tools for the Team (Simulating VR and Voice Analysis) ---
@tool(name="analyze_vocal_tone")
def analyze_vocal_tone(context: AgentContextType, user_text: str) -> str:
    """
    Simulates analyzing the emotional tone from a user's text input.
    In a real app, this would use a sophisticated speech-to-text and tone analysis model.
    """
    text = user_text.lower()
    emotion = "neutral"
    confidence = 0.7
    if re.search(r'\b(stuck|frustrated|angry|can\'t)\b', text):
        emotion = "frustration"
        confidence = 0.85
    elif re.search(r'\b(sad|empty|lost|uninspired)\b', text):
        emotion = "sadness"
        confidence = 0.80
    elif re.search(r'\b(anxious|worried|nervous)\b', text):
        emotion = "anxiety"
        confidence = 0.90
    
    result = {"detected_emotion": emotion, "confidence": confidence}
    logging.info(f"Tool 'analyze_vocal_tone' processed text and found emotion: {emotion}")
    return json.dumps(result)

@tool(name="set_vr_environment")
def set_vr_environment(context: AgentContextType, theme: str, elements: list) -> str:
    """
    Simulates changing the user's virtual reality environment.
    In a real application, this would call the VR engine's API.
    """
    log_message = f"VR ENGINE: Setting environment to theme '{theme}' with elements: {', '.join(elements)}."
    print(f"\n--- [TOOL LOG] {log_message} ---\n") # Make it visible in the TUI for effect
    logging.info(f"Agent '{context.agent_id}' executed set_vr_environment. {log_message}")

    workspace = context.workspace
    if workspace:
        log_file_path = os.path.join(workspace.get_base_path(), "vr_environment_log.txt")
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] {log_message}\n")

    return f"Environment successfully set to '{theme}'."


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
        return "simple_local_workspace_for_vr_therapy"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the VR Therapy team to store session notes."

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
    log_file_path = log_dir / "team_vr_therapy_run.log"
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
def create_vr_therapy_team(llm_model: str, workspace: BaseAgentWorkspace):
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="AI Therapist", role="Coordinator",
        description="The main conversational agent that interacts with the user and orchestrates the session.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[SendMessageTo(), file_writer],
        workspace=workspace
    )
    vocal_analyst_config = AgentConfig(
        name="Vocal Analyst", role="Specialist",
        description="Analyzes the user's speech (simulated as text) to detect their emotional state.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["vocal_analyst"],
        tools=[SendMessageTo(), analyze_vocal_tone],
        workspace=workspace
    )
    cognitive_specialist_config = AgentConfig(
        name="Cognitive Specialist", role="Specialist",
        description="Devises therapeutic techniques and creative exercises based on the user's state.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["cognitive_specialist"],
        tools=[SendMessageTo()],
        workspace=workspace
    )
    environment_weaver_config = AgentConfig(
        name="Environment Weaver", role="Specialist",
        description="Controls the simulated VR environment based on instructions.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["environment_weaver"],
        tools=[SendMessageTo(), set_vr_environment],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="VRTherapyTeam", description="An AI team that provides immersive therapy for creative blocks.")
        .set_coordinator(coordinator_config)
        .add_agent_node(vocal_analyst_config)
        .add_agent_node(cognitive_specialist_config)
        .add_agent_node(environment_weaver_config)
        .set_task_notification_mode(TaskNotificationMode.AGENT_MANUAL_NOTIFICATION) # Conversational flow
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'VR-enhanced AI Therapy' team...")
    print("NOTE: VR and voice analysis are simulated via text and log output.")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace for session notes is set to: {workspace_path}")

    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_vr_therapy_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the VR-enhanced AI Therapy for Creative Blocks team.",
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
        default="./vr_therapy_workspace",
        help="Directory for the shared agent workspace, where session notes will be stored."
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