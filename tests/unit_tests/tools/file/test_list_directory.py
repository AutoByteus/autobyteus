import pytest
from pathlib import Path
from unittest.mock import Mock
import os

# Import the module to ensure the tool is registered
import autobyteus.tools.file.list_directory
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.context import AgentContext
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

TOOL_NAME_LIST_DIRECTORY = "list_directory"

# --- Fixtures ---

@pytest.fixture
def mock_agent_context() -> AgentContext:
    """Provides a mock AgentContext with no workspace by default."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_list_directory"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def list_directory_tool_instance(mock_agent_context: AgentContext) -> BaseTool:
    """Provides an instance of the list_directory tool."""
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_LIST_DIRECTORY)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context.agent_id)
    return tool_instance

@pytest.fixture
def test_dir_structure(tmp_path: Path) -> Path:
    """Creates a standard nested directory structure for testing."""
    root_dir = tmp_path / "test_root"
    sub_dir = root_dir / "sub"
    deep_sub_dir = sub_dir / "deep_sub"
    
    deep_sub_dir.mkdir(parents=True)
    
    (root_dir / "z.txt").write_text("zeta")
    (root_dir / "a.txt").write_text("alpha")
    (sub_dir / "b.txt").write_text("beta")
    (deep_sub_dir / "c.txt").write_text("gamma")
    
    return root_dir

# --- Tests ---

def test_list_directory_definition():
    """Tests if the list_directory tool is defined correctly."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_LIST_DIRECTORY)
    assert definition is not None
    assert definition.name == TOOL_NAME_LIST_DIRECTORY
    assert "Lists the contents of a directory" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 4

    path_param = schema.get_parameter("path")
    assert path_param.param_type == ParameterType.STRING
    assert path_param.required is True

    depth_param = schema.get_parameter("depth")
    assert depth_param.param_type == ParameterType.INTEGER
    assert depth_param.default_value == 2

    limit_param = schema.get_parameter("limit")
    assert limit_param.param_type == ParameterType.INTEGER
    assert limit_param.default_value == 25

    offset_param = schema.get_parameter("offset")
    assert offset_param.param_type == ParameterType.INTEGER
    assert offset_param.default_value == 1

@pytest.mark.asyncio
async def test_list_directory_basic_defaults(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path):
    """Tests basic listing with default depth=2."""
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure)
    )
    
    expected_lines = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] a.txt",
        "├─ [dir] sub",
        "├─ [file] z.txt",
        "  ├─ [file] b.txt",
        "  └─ [dir] deep_sub",
    ]
    
    assert result == "\n".join(expected_lines)

@pytest.mark.asyncio
async def test_list_directory_depth_1(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path):
    """Tests listing with depth=1, showing only the top level."""
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure),
        depth=1
    )
    
    expected_lines = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] a.txt",
        "├─ [dir] sub",
        "└─ [file] z.txt",
    ]
    
    assert result == "\n".join(expected_lines)

@pytest.mark.asyncio
async def test_list_directory_full_depth(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path):
    """Tests listing with depth=3, showing all nested files."""
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure),
        depth=3
    )
    
    expected_lines = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] a.txt",
        "├─ [dir] sub",
        "├─ [file] z.txt",
        "  ├─ [file] b.txt",
        "  ├─ [dir] deep_sub",
        "    └─ [file] c.txt",
    ]
    
    assert result == "\n".join(expected_lines)

@pytest.mark.asyncio
async def test_list_directory_relative_path_with_workspace(
    list_directory_tool_instance: BaseTool,
    mock_agent_context: AgentContext,
    test_dir_structure: Path
):
    """Tests that a relative path is correctly resolved when a workspace is present."""
    # Set up a mock workspace on the context
    mock_workspace = Mock()
    mock_workspace.get_base_path.return_value = str(test_dir_structure)
    mock_agent_context.workspace = mock_workspace

    # Execute with a relative path "."
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path="."
    )
    
    expected_lines = [
        f"Absolute path: {os.path.normpath(str(test_dir_structure))}",
        "├─ [file] a.txt",
        "├─ [dir] sub",
        "├─ [file] z.txt",
        "  ├─ [file] b.txt",
        "  └─ [dir] deep_sub",
    ]
    assert result == "\n".join(expected_lines)

    # Execute with a relative path to a subdirectory
    result_sub = await list_directory_tool_instance.execute(
        mock_agent_context,
        path="sub"
    )
    
    sub_path = os.path.normpath(str(test_dir_structure / "sub"))
    expected_lines_sub = [
        f"Absolute path: {sub_path}",
        "├─ [file] b.txt",
        "├─ [dir] deep_sub",
        "  └─ [file] c.txt",
    ]
    assert result_sub == "\n".join(expected_lines_sub)

@pytest.mark.asyncio
async def test_list_directory_pagination(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path):
    """Tests the limit and offset parameters for pagination."""
    # First page
    result_page1 = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure),
        depth=3,
        limit=2,
        offset=1
    )
    
    expected_page1 = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] a.txt",
        "└─ [dir] sub",
        "More than 2 entries found.",
    ]
    assert result_page1 == "\n".join(expected_page1)

    # Second page
    result_page2 = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure),
        depth=3,
        limit=3,
        offset=3
    )
    
    expected_page2 = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] z.txt",
        "  ├─ [file] b.txt",
        "  └─ [dir] deep_sub",
        "More than 3 entries found.",
    ]
    assert result_page2 == "\n".join(expected_page2)

@pytest.mark.asyncio
async def test_list_directory_empty_dir(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, tmp_path: Path):
    """Tests listing an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(empty_dir)
    )
    
    assert result == f"Absolute path: {empty_dir}"

@pytest.mark.asyncio
async def test_list_directory_validation_errors(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path):
    """Tests that validation errors are raised for invalid arguments."""
    # Relative path without a workspace should fail
    mock_agent_context.workspace = None
    with pytest.raises(ValueError, match="no workspace is configured"):
        await list_directory_tool_instance.execute(mock_agent_context, path=".")

    # Non-existent path
    non_existent_path = test_dir_structure / "non_existent"
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        await list_directory_tool_instance.execute(mock_agent_context, path=str(non_existent_path))

    # Path is a file
    file_path = test_dir_structure / "a.txt"
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        await list_directory_tool_instance.execute(mock_agent_context, path=str(file_path))

    # Invalid depth, limit, offset
    for param in ["depth", "limit", "offset"]:
        with pytest.raises(ValueError, match="must all be greater than zero"):
            kwargs = {"path": str(test_dir_structure), param: 0}
            await list_directory_tool_instance.execute(mock_agent_context, **kwargs)

@pytest.mark.asyncio
async def test_list_directory_permission_error(list_directory_tool_instance: BaseTool, mock_agent_context: AgentContext, test_dir_structure: Path, mocker):
    """Tests graceful handling of PermissionError when scanning a directory."""
    # Mock os.scandir to raise PermissionError when it tries to scan inside the 'sub' directory.
    original_scandir = os.scandir
    def mock_scandir(path):
        if Path(path) == test_dir_structure / "sub":
            raise PermissionError("Access denied")
        return original_scandir(path)

    mocker.patch('autobyteus.tools.file.list_directory.os.scandir', side_effect=mock_scandir)

    # The tool should still return results from accessible directories.
    result = await list_directory_tool_instance.execute(
        mock_agent_context,
        path=str(test_dir_structure),
        depth=3
    )

    # 'sub' and its children will be missing, but the tool completes.
    expected_lines = [
        f"Absolute path: {test_dir_structure}",
        "├─ [file] a.txt",
        "├─ [dir] sub",  # The entry for sub itself is found before scandir is called on it
        "└─ [file] z.txt",
    ]

    assert result == "\n".join(expected_lines)
