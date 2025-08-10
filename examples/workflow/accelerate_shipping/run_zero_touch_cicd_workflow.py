import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

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
    from autobyteus.tools import file_writer, file_reader, bash_executor
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    sys.exit(1)

# --- Custom Workspace (re-used from example for simplicity) ---
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
        return "simple_local_workspace_for_cicd"
    @classmethod
    def get_description(cls) -> str:
        return "A basic workspace for local file access for the CI/CD workflow."
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
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "zero_touch_cicd_workflow.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path

# --- Workflow Definition ---
def create_ci_cd_workflow(
    llm_model: str, 
    workspace: BaseAgentWorkspace,
    use_xml_tool_format: bool = True
):
    orchestrator_config = AgentConfig(
        name="PipelineOrchestrator", role="CI/CD Manager",
        description="Manages the automated code analysis, testing, and release note generation pipeline.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are the orchestrator of a fully automated CI/CD pipeline. Your goal is to process a feature description and a list of changed files from an engineer and see it through analysis, testing, and documentation.\n"
            "You must manage a team of specialists and follow this sequence EXACTLY:\n"
            "1.  **Analyze Code:** Instruct the `CodeAnalyzer` to read the changed files and provide a detailed analysis of code quality, style, and potential bugs.\n"
            "2.  **Generate Tests:** Once the analysis is complete, instruct the `UnitTestGenerator` to read the changed files and write comprehensive pytest unit tests. It must save these tests to a new file named `test_feature.py`.\n"
            "3.  **Run Tests:** After the tests are written, instruct the `IntegrationTester` to execute the entire test suite by running the `pytest` command.\n"
            "4.  **Draft Release Notes:** Based on the user's initial feature description and the analysis from the `CodeAnalyzer`, instruct the `ReleaseNotesDrafter` to write clear, concise release notes for this feature.\n"
            "5.  **Final Report:** Once all steps are complete, compile a final report for the user including the analysis summary, test results (pass/fail), and the drafted release notes. This is your final output.\n\n"
            "**CRITICAL:** You must wait for each agent to confirm completion before proceeding to the next. Do not combine steps. Be methodical and precise.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    analyzer_config = AgentConfig(
        name="CodeAnalyzer", role="Senior Engineer",
        description="Reads code files and provides a quality and style analysis.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a senior software engineer responsible for code quality. Your task is to read the specified code file(s) using the `FileReader` tool. "
            "Provide a concise summary of the changes, check for adherence to PEP 8 style guidelines, and identify any potential bugs, logical errors, or areas for improvement. "
            "Present your findings in a clear, bulleted list to the PipelineOrchestrator.\n\n{{tools}}"
        ),
        tools=[file_reader],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    test_generator_config = AgentConfig(
        name="UnitTestGenerator", role="QA Engineer",
        description="Writes pytest unit tests for given code files.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a QA Engineer specializing in automated testing. Your task is to read a Python source file and write a comprehensive suite of unit tests using the `pytest` framework. "
            "You MUST save the generated tests to the filename specified by the PipelineOrchestrator using the `FileWriter` tool. Your tests should cover edge cases and common use cases.\n\n{{tools}}"
        ),
        tools=[file_reader, file_writer],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    tester_config = AgentConfig(
        name="IntegrationTester", role="DevOps Engineer",
        description="Executes test suites using shell commands.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a DevOps Engineer. Your role is to run tests. You will be instructed by the PipelineOrchestrator to run the test suite. "
            "You MUST use the `BashExecutor` tool to run the command `pytest`. Report the full, raw output back to the orchestrator.\n\n{{tools}}"
        ),
        tools=[bash_executor],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    releasenotes_config = AgentConfig(
        name="ReleaseNotesDrafter", role="Technical Writer",
        description="Drafts release notes based on feature descriptions and code analysis.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Technical Writer. You will be given a feature description and a code analysis report. "
            "Your task is to synthesize this information into a clear, user-facing release note. "
            "Focus on the user benefit and the problem solved. Do not use technical jargon. "
            "Present the final draft to the PipelineOrchestrator."
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    ci_cd_workflow = (
        WorkflowBuilder(name="ZeroTouchCICDPipeline", description="An automated pipeline for code analysis, testing, and release note generation.")
        .set_coordinator(orchestrator_config)
        .add_agent_node(analyzer_config)
        .add_agent_node(test_generator_config)
        .add_agent_node(tester_config)
        .add_agent_node(releasenotes_config)
        .build()
    )
    return ci_cd_workflow

async def main(args: argparse.Namespace, log_file: Path):
    print("Setting up Zero-Touch CI/CD Pipeline workflow...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace (output directory) is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)
    
    # Create a dummy file for the agents to work on
    dummy_code = "def add(a, b):\n    return a + b\n"
    dummy_file_path = workspace_path / "feature.py"
    with open(dummy_file_path, "w") as f:
        f.write(dummy_code)
    print(f"--> Created dummy code file at: {dummy_file_path}")
    print("\n----------------------------------------------------")
    print("Workflow is ready. In the TUI, start with a prompt like this:")
    print(f'Please process the new feature "Add two numbers" with the changed file "feature.py"')
    print("----------------------------------------------------\n")

    use_xml_tool_format = not args.no_xml_tools
    try:
        workflow = create_ci_cd_workflow(
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
    parser = argparse.ArgumentParser(description="Run an automated CI/CD pipeline workflow with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model for all agents.")
    parser.add_argument("--output-dir", type=str, default="./cicd_pipeline_output", help="Directory for the shared workspace.")
    parser.add_argument("--no-xml-tools", action="store_true", help="Disable XML-based tool formatting.")
    parsed_args = parser.parse_args()
    log_file_path = setup_file_logging()
    try:
        asyncio.run(main(parsed_args, log_file_path))
    except KeyboardInterrupt:
        print("\nExiting application.")