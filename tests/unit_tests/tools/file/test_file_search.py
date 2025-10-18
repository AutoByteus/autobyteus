import pytest
import os
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import autobyteus.tools.file.search_files

from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

TOOL_NAME_SEARCH_FILES = "search_files"

# --- Fixtures ---

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_file_search"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def file_search_tool_instance(mock_agent_context: AgentContext) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_SEARCH_FILES)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context.agent_id)
    return tool_instance

@pytest.fixture
def git_repo_path(tmp_path: Path) -> Path:
    """Creates a temporary Git repository with a standard file structure."""
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()
    
    # Create files
    (repo_dir / "README.md").write_text("Project Readme")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "main.py").write_text("print('hello')")
    (repo_dir / "src" / "utils.py").write_text("# utilities")
    (repo_dir / "data").mkdir()
    (repo_dir / "data" / "config.json").write_text("{}")
    (repo_dir / ".env").write_text("SECRET=123") # Should be ignored
    (repo_dir / "untracked.log").write_text("log data")

    # Create .gitignore
    (repo_dir / ".gitignore").write_text("*.log\n.env")

    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True, capture_output=True)
    
    return repo_dir

@pytest.fixture
def non_git_path(tmp_path: Path) -> Path:
    """Creates a temporary directory that is NOT a git repo."""
    non_git_dir = tmp_path / "non_git_dir"
    non_git_dir.mkdir()
    
    # Create files
    (non_git_dir / "document.txt").write_text("some text")
    (non_git_dir / "scripts").mkdir()
    (non_git_dir / "scripts" / "run.sh").write_text("echo 'run'")
    (non_git_dir / "archive.zip").write_text("zip")
    (non_git_dir / "logs").mkdir()
    (non_git_dir / "logs" / "app.log").write_text("log data")

    # Create .gitignore
    (non_git_dir / ".gitignore").write_text("*.zip\n/logs/")
    
    return non_git_dir

# --- Tests ---

def test_file_search_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_SEARCH_FILES)
    assert definition is not None
    assert definition.name == TOOL_NAME_SEARCH_FILES
    assert "Performs a high-performance fuzzy search" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 4

    query_param = schema.get_parameter("query")
    assert query_param.param_type == ParameterType.STRING
    assert query_param.required is False

    path_param = schema.get_parameter("path")
    assert path_param.param_type == ParameterType.STRING
    assert path_param.required is False
    assert path_param.default_value == "."

    limit_param = schema.get_parameter("limit")
    assert limit_param.param_type == ParameterType.INTEGER
    assert limit_param.required is False
    assert limit_param.default_value == 64

    exclude_param = schema.get_parameter("exclude_patterns")
    assert exclude_param.param_type == ParameterType.ARRAY
    assert exclude_param.required is False

@pytest.mark.asyncio
async def test_search_in_git_repo_fuzzy(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, git_repo_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(git_repo_path),
        query="main"
    )
    result = json.loads(result_str)
    assert result["discovery_method"] == "git"
    assert len(result["results"]) == 1
    assert result["results"][0]["path"] == "src/main.py"
    assert result["results"][0]["score"] > 80

@pytest.mark.asyncio
async def test_search_in_git_repo_list_all(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, git_repo_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(git_repo_path)
    )
    result = json.loads(result_str)
    paths = {item["path"] for item in result["results"]}
    
    assert "src/main.py" in paths
    assert "README.md" in paths
    assert ".gitignore" in paths
    assert "untracked.log" not in paths # Ignored by .gitignore in git ls-files -co
    assert ".env" not in paths # Ignored by .gitignore

@pytest.mark.asyncio
async def test_search_in_git_repo_with_exclude(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, git_repo_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(git_repo_path),
        exclude_patterns=["*.py"]
    )
    result = json.loads(result_str)
    paths = {item["path"] for item in result["results"]}

    assert "src/main.py" not in paths
    assert "src/utils.py" not in paths
    assert "README.md" in paths

@pytest.mark.asyncio
async def test_search_in_non_git_dir_fuzzy(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, non_git_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(non_git_path),
        query="script"
    )
    result = json.loads(result_str)
    assert result["discovery_method"] == "os_walk"
    assert len(result["results"]) > 0
    assert result["results"][0]["path"] == os.path.join("scripts", "run.sh")

@pytest.mark.asyncio
async def test_search_in_non_git_dir_respects_gitignore(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, non_git_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(non_git_path)
    )
    result = json.loads(result_str)
    paths = {item["path"] for item in result["results"]}

    assert "archive.zip" not in paths
    assert os.path.join("logs", "app.log") not in paths
    assert "document.txt" in paths

@pytest.mark.asyncio
async def test_search_limit_parameter(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, git_repo_path: Path):
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path=str(git_repo_path),
        limit=2
    )
    result = json.loads(result_str)
    assert len(result["results"]) == 2

@pytest.mark.asyncio
async def test_search_path_not_found(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, tmp_path: Path):
    non_existent_path = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        await file_search_tool_instance.execute(
            mock_agent_context,
            path=str(non_existent_path)
        )

@pytest.mark.asyncio
async def test_search_relative_path_with_workspace(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext, git_repo_path: Path):
    # Mock the workspace to point to our temp git repo
    mock_workspace = Mock()
    mock_workspace.get_base_path.return_value = str(git_repo_path)
    mock_agent_context.workspace = mock_workspace

    # Search in a subdirectory using a relative path
    result_str = await file_search_tool_instance.execute(
        mock_agent_context,
        path="src"
    )
    result = json.loads(result_str)
    paths = {item["path"] for item in result["results"]}

    # Results should be relative to the new search root (git_repo_path/src)
    assert "main.py" in paths
    assert "utils.py" in paths
    assert len(paths) == 2

@pytest.mark.asyncio
async def test_search_relative_path_no_workspace(file_search_tool_instance: BaseTool, mock_agent_context: AgentContext):
    # Ensure workspace is None
    mock_agent_context.workspace = None
    with pytest.raises(ValueError, match="Relative path 'src' provided, but no workspace is configured"):
        await file_search_tool_instance.execute(
            mock_agent_context,
            path="src"
        )
