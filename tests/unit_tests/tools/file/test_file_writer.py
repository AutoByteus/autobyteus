import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock

import autobyteus.tools.file.write_file 

from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

TOOL_NAME_WRITE_FILE = "write_file"

@pytest.fixture
def mock_agent_context_file_ops() -> AgentContext: 
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_file_ops_func_writer"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def file_writer_tool_instance(mock_agent_context_file_ops: AgentContext) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_WRITE_FILE)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context_file_ops.agent_id)
    return tool_instance

@pytest.fixture
def mock_agent_context_with_workspace(temp_dir_for_functional_writer: str) -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_file_ops_func_writer_workspace"
    mock_workspace = Mock()
    mock_workspace.get_base_path.return_value = temp_dir_for_functional_writer
    mock_context.workspace = mock_workspace
    return mock_context

@pytest.fixture
def temp_dir_for_functional_writer() -> str:  # type: ignore
    base_temp_dir = tempfile.gettempdir()
    test_specific_dir = os.path.join(base_temp_dir, f"autobyteus_func_writer_{os.urandom(4).hex()}")
    os.makedirs(test_specific_dir, exist_ok=True)
    yield test_specific_dir
    shutil.rmtree(test_specific_dir, ignore_errors=True)

def test_file_writer_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_WRITE_FILE)
    assert definition is not None 
    assert definition.name == TOOL_NAME_WRITE_FILE
    assert "Creates or overwrites a file" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2 
    
    param_path = schema.get_parameter("path")
    assert isinstance(param_path, ParameterDefinition)
    assert param_path.param_type == ParameterType.STRING # MODIFIED from FILE_PATH
    assert param_path.required is True
    assert "Parameter 'path' for tool 'write_file'" in param_path.description
    assert "This is expected to be a path." in param_path.description # Heuristic added description
    
    param_content = schema.get_parameter("content")
    assert isinstance(param_content, ParameterDefinition)
    assert param_content.param_type == ParameterType.STRING
    assert param_content.required is True
    assert "Parameter 'content' for tool 'write_file'" in param_content.description

@pytest.mark.asyncio
async def test_create_file_functional(file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "test_writer1.txt")
    content = "Functional Test Content 1 with Ümlauts"
    expected_message = f"File created/updated at {path}"
    
    result = await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content=content)
    assert result == expected_message
    with open(path, 'r', encoding='utf-8') as file:
        assert file.read() == content

@pytest.mark.asyncio
async def test_create_file_in_new_dir_functional(file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "new_subdir", "test_writer2.txt")
    content = "Content in new subdir"
    expected_message = f"File created/updated at {path}"
    
    result = await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content=content)
    assert result == expected_message
    with open(path, 'r', encoding='utf-8') as file:
        assert file.read() == content

@pytest.mark.asyncio
async def test_write_missing_path_functional(file_writer_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_WRITE_FILE}'"):
        await file_writer_tool_instance.execute(mock_agent_context_file_ops, content="Test Content")

@pytest.mark.asyncio
async def test_write_missing_content_functional(file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "test_writer_no_content.txt")
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_WRITE_FILE}'"):
        await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path)

@pytest.mark.asyncio
async def test_write_empty_content_functional(file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "empty_writer_file.txt")
    content = ""
    expected_message = f"File created/updated at {path}"
    result = await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content=content)
    assert result == expected_message
    with open(path, 'r', encoding='utf-8') as file:
        assert file.read() == content

@pytest.mark.asyncio
async def test_overwrite_existing_file_functional(file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "existing_writer_file.txt")
    await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content="Initial")
    
    new_content = "Overwritten Functional Content"
    expected_message = f"File created/updated at {path}"
    result = await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content=new_content)
    assert result == expected_message
    with open(path, 'r', encoding='utf-8') as file:
        assert file.read() == new_content

@pytest.mark.asyncio
async def test_write_io_error_functional(mocker, file_writer_tool_instance: BaseTool, temp_dir_for_functional_writer: str, mock_agent_context_file_ops: AgentContext):
    path = os.path.join(temp_dir_for_functional_writer, "writer_io_error.txt")
    mocker.patch('autobyteus.tools.file.write_file.os.makedirs') 
    mocker.patch('autobyteus.tools.file.write_file.open', side_effect=IOError("Simulated write permission denied"))
    
    with pytest.raises(IOError, match=f"Could not write file at '{path}': Simulated write permission denied"):
        await file_writer_tool_instance.execute(mock_agent_context_file_ops, path=path, content="test")

@pytest.mark.asyncio
async def test_write_relative_path_returns_relative(
    file_writer_tool_instance: BaseTool,
    temp_dir_for_functional_writer: str,
    mock_agent_context_with_workspace: AgentContext,
):
    rel_path = os.path.join("subdir", "relative.txt")
    content = "Relative content"
    expected_message = f"File created/updated at {os.path.normpath(rel_path)}"

    result = await file_writer_tool_instance.execute(
        mock_agent_context_with_workspace,
        path=rel_path,
        content=content,
    )
    assert result == expected_message

    full_path = os.path.join(temp_dir_for_functional_writer, rel_path)
    with open(full_path, 'r', encoding='utf-8') as file:
        assert file.read() == content
