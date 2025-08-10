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
    from autobyteus.tools import file_writer, file_reader
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
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
        return "simple_local_workspace_for_scaffolding"
    @classmethod
    def get_description(cls) -> str:
        return "A basic workspace for local file access for the API scaffolding workflow."
    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        return ParameterSchema().add_parameter(ParameterDefinition(
            name="root_path", param_type=ParameterType.STRING,
            description="The absolute local file path for the workspace root.", required=True
        ))

def setup_file_logging() -> Path:
    log_dir = PACKAGE_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "api_scaffolding_workflow.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    return log_file_path

# --- Workflow Definition ---
def create_api_scaffolding_workflow(
    llm_model: str, 
    workspace: BaseAgentWorkspace,
    use_xml_tool_format: bool = True
):
    architect_config = AgentConfig(
        name="FeatureArchitect", role="Lead Software Architect",
        description="Designs and orchestrates the creation of new API features.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Lead Software Architect managing a team of specialist agents to rapidly scaffold new API features. You will receive a high-level feature specification from a user.\n"
            "Your process must be as follows:\n"
            "1.  **PARALLEL DELEGATION:** Delegate the following tasks to your team SIMULTANEOUSLY:\n"
            "    a. Instruct `APICoder` to write the FastAPI endpoint logic and save it to `api/endpoints/feature.py`.\n"
            "    b. Instruct `DataModeler` to create the Pydantic request/response models and save them to `api/models/feature_models.py`.\n"
            "    c. Instruct `DocWriter` to write a markdown documentation file for the new feature and save it to `docs/feature.md`.\n"
            "2.  **SYNCHRONIZE:** You MUST wait until you have received confirmation of completion from ALL THREE agents (`APICoder`, `DataModeler`, `DocWriter`) before proceeding.\n"
            "3.  **TEST GENERATION:** Once all components are created, instruct the `TestCoder` to read the new files and write `pytest` tests, saving them to `tests/test_feature.py`.\n"
            "4.  **REPORT COMPLETION:** After the `TestCoder` confirms completion, report to the user that all scaffolding artifacts have been successfully generated.\n\n"
            "**CRITICAL RULE:** The first phase of delegation is PARALLEL. You must initiate all three tasks before waiting for any of them to finish. Your efficiency is paramount.\n\n{{tools}}"
        ),
        use_xml_tool_format=use_xml_tool_format
    )

    api_coder_config = AgentConfig(
        name="APICoder", role="Backend Engineer",
        description="Writes FastAPI endpoint logic.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Backend Engineer specializing in FastAPI. You will receive a feature specification from the FeatureArchitect. "
            "Your task is to write clean, efficient Python code for the API endpoint. You MUST use the `FileWriter` tool to save the code to the specified path. "
            "Assume necessary data models will be available from an import.\n\n{{tools}}"
        ),
        tools=[file_writer],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    data_modeler_config = AgentConfig(
        name="DataModeler", role="Data Engineer",
        description="Creates Pydantic data models.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Data Engineer. Your task is to create Pydantic models for API requests and responses based on a feature specification. "
            "You MUST use the `FileWriter` tool to save these models to the specified Python file.\n\n{{tools}}"
        ),
        tools=[file_writer],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    doc_writer_config = AgentConfig(
        name="DocWriter", role="Technical Writer",
        description="Writes technical documentation.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a Technical Writer. Based on the feature specification, write a clear markdown document explaining the new API endpoint, its parameters, and expected responses. "
            "You MUST use the `FileWriter` tool to save the documentation to the specified file.\n\n{{tools}}"
        ),
        tools=[file_writer],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    test_coder_config = AgentConfig(
        name="TestCoder", role="QA Engineer",
        description="Writes pytest tests for API endpoints.",
        llm_instance=default_llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=(
            "You are a QA Engineer. You will be given the file paths for a new API endpoint and its data models. "
            "Your task is to read these files using the `FileReader` tool, write comprehensive pytest tests covering the endpoint's functionality, and save them to the specified test file using the `FileWriter` tool.\n\n{{tools}}"
        ),
        tools=[file_reader, file_writer],
        workspace=workspace,
        use_xml_tool_format=use_xml_tool_format
    )

    scaffolding_workflow = (
        WorkflowBuilder(name="APIFeatureScaffolding", description="A parallel workflow to rapidly generate code, models, docs, and tests for a new API feature.")
        .set_coordinator(architect_config)
        .add_agent_node(api_coder_config)
        .add_agent_node(data_modeler_config)
        .add_agent_node(doc_writer_config)
        .add_agent_node(test_coder_config)
        .build()
    )
    return scaffolding_workflow

async def main(args: argparse.Namespace, log_file: Path):
    print("Setting up Parallel API Feature Scaffolding workflow...")
    print(f"--> Logs will be written to: {log_file.resolve()}")
    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace (output directory) is set to: {workspace_path}")
    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    print("\n----------------------------------------------------")
    print("Workflow is ready. In the TUI, start with a prompt like this:")
    print('Scaffold a new API feature for a user profile. It should be a GET endpoint at /users/{user_id} that returns a User model with id, username, and email. The endpoint should just return a mock user for now.')
    print("----------------------------------------------------\n")
    
    use_xml_tool_format = not args.no_xml_tools
    try:
        workflow = create_api_scaffolding_workflow(
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
    parser = argparse.ArgumentParser(description="Run a parallel API scaffolding workflow with a Textual TUI.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model for all agents.")
    parser.add_argument("--output-dir", type=str, default="./api_scaffolding_output", help="Directory for the shared workspace.")
    parser.add_argument("--no-xml-tools", action="store_true", help="Disable XML-based tool formatting.")
    parsed_args = parser.parse_args()
    log_file_path = setup_file_logging()
    try:
        asyncio.run(main(parsed_args, log_file_path))
    except KeyboardInterrupt:
        print("\nExiting application.")