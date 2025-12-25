import pytest
import os
from unittest.mock import Mock
import xml.sax.saxutils

import autobyteus.tools.file.read_file 

from autobyteus.tools.registry import default_tool_registry 
from autobyteus.tools.base_tool import BaseTool 
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext

TOOL_NAME_READ_FILE = "read_file"

@pytest.fixture
def mock_agent_context_file_ops() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_file_ops_func_reader"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def file_reader_tool_instance(mock_agent_context_file_ops: AgentContext) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_READ_FILE)
    assert isinstance(tool_instance, BaseTool) 
    tool_instance.set_agent_id(mock_agent_context_file_ops.agent_id)
    return tool_instance

@pytest.fixture
def test_file_for_reader(tmp_path): 
    file_path = tmp_path / "test_file_reader.txt"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("Test Content with Ümlauts for read_file")
    return file_path

def test_file_reader_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_READ_FILE)
    assert definition is not None 
    assert definition.name == TOOL_NAME_READ_FILE
    assert "Reads content from a specified file" in definition.description
    assert "Raises FileNotFoundError if the file does not exist" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 3 
    
    param_path = schema.get_parameter("path")
    assert isinstance(param_path, ParameterDefinition)
    assert param_path.name == "path"
    assert param_path.param_type == ParameterType.STRING # MODIFIED from FILE_PATH
    assert param_path.required is True
    assert "Parameter 'path' for tool 'read_file'" in param_path.description
    assert "This is expected to be a path." in param_path.description # Heuristic added description

    param_start_line = schema.get_parameter("start_line")
    assert isinstance(param_start_line, ParameterDefinition)
    assert param_start_line.name == "start_line"
    assert param_start_line.param_type == ParameterType.INTEGER
    assert param_start_line.required is False

    param_end_line = schema.get_parameter("end_line")
    assert isinstance(param_end_line, ParameterDefinition)
    assert param_end_line.name == "end_line"
    assert param_end_line.param_type == ParameterType.INTEGER
    assert param_end_line.required is False

def test_file_reader_tool_usage_xml_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_READ_FILE)
    assert definition is not None
    xml_output = definition.get_usage_xml()
    
    description = definition.description
    escaped_desc = xml.sax.saxutils.escape(description)
    assert f'<tool name="{TOOL_NAME_READ_FILE}" description="{escaped_desc}">' in xml_output
    
    expected_param_desc = "Parameter 'path' for tool 'read_file'. This is expected to be a path."
    escaped_param_desc = xml.sax.saxutils.escape(expected_param_desc)
    assert f'<arg name="path" type="string" description="{escaped_param_desc}" required="true" />' in xml_output
    expected_start_line_desc = "Parameter 'start_line' for tool 'read_file'."
    escaped_start_line_desc = xml.sax.saxutils.escape(expected_start_line_desc)
    assert f'<arg name="start_line" type="integer" description="{escaped_start_line_desc}" required="false" />' in xml_output
    expected_end_line_desc = "Parameter 'end_line' for tool 'read_file'."
    escaped_end_line_desc = xml.sax.saxutils.escape(expected_end_line_desc)
    assert f'<arg name="end_line" type="integer" description="{escaped_end_line_desc}" required="false" />' in xml_output
    assert '</tool>' in xml_output

def test_file_reader_tool_usage_json_output():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_READ_FILE)
    assert definition is not None
    json_output = definition.get_usage_json()

    assert json_output["name"] == TOOL_NAME_READ_FILE
    assert "Reads content from a specified file" in json_output["description"]
    
    input_schema = json_output["inputSchema"]
    assert input_schema["type"] == "object"
    assert "path" in input_schema["properties"]
    path_prop = input_schema["properties"]["path"]
    assert path_prop["type"] == ParameterType.STRING.to_json_schema_type() # Was FILE_PATH but mapped to string
    assert "Parameter 'path' for tool 'read_file'" in path_prop["description"]
    assert "This is expected to be a path." in path_prop["description"]
    assert "path" in input_schema["required"]

    start_line_prop = input_schema["properties"]["start_line"]
    assert start_line_prop["type"] == ParameterType.INTEGER.to_json_schema_type()

    end_line_prop = input_schema["properties"]["end_line"]
    assert end_line_prop["type"] == ParameterType.INTEGER.to_json_schema_type()

@pytest.mark.asyncio
async def test_read_file_content_functional(file_reader_tool_instance: BaseTool, test_file_for_reader: str, mock_agent_context_file_ops: AgentContext):
    content = await file_reader_tool_instance.execute(mock_agent_context_file_ops, path=str(test_file_for_reader))
    assert content == "1: Test Content with Ümlauts for read_file"

@pytest.mark.asyncio
async def test_read_file_with_line_range_functional(tmp_path, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    file_path = tmp_path / "range_reader_file.txt"
    file_path.write_text("line1\nline2\nline3\n", encoding="utf-8")

    content = await file_reader_tool_instance.execute(
        mock_agent_context_file_ops,
        path=str(file_path),
        start_line=2,
        end_line=3
    )
    assert content == "2: line2\n3: line3\n"

@pytest.mark.asyncio
async def test_read_file_invalid_line_range_functional(tmp_path, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    file_path = tmp_path / "invalid_range_reader_file.txt"
    file_path.write_text("line1\nline2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="end_line .* must be >= start_line"):
        await file_reader_tool_instance.execute(
            mock_agent_context_file_ops,
            path=str(file_path),
            start_line=3,
            end_line=2
        )

@pytest.mark.asyncio
async def test_read_non_existent_file_functional(tmp_path, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    mock_agent_context_file_ops.workspace = Mock()
    mock_agent_context_file_ops.workspace.get_base_path.return_value = str(tmp_path)
    with pytest.raises(FileNotFoundError): 
        await file_reader_tool_instance.execute(mock_agent_context_file_ops, path="non_existent_reader_file.txt")

@pytest.mark.asyncio
async def test_read_missing_path_arg_functional(file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    with pytest.raises(ValueError, match=f"Invalid arguments for tool '{TOOL_NAME_READ_FILE}'"):
        await file_reader_tool_instance.execute(mock_agent_context_file_ops)

@pytest.mark.asyncio
async def test_read_relative_path_functional(tmp_path, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    mock_agent_context_file_ops.workspace = Mock()
    mock_agent_context_file_ops.workspace.get_base_path.return_value = str(tmp_path)
    file_path_str = "relative_reader_test.txt"
    with open(file_path_str, 'w', encoding='utf-8') as f:
        f.write("Relative path content for read_file")
    
    content = await file_reader_tool_instance.execute(mock_agent_context_file_ops, path=file_path_str)
    assert content == "1: Relative path content for read_file"
    os.chdir(original_cwd)

@pytest.mark.asyncio
async def test_read_empty_file_functional(tmp_path, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    file_path = tmp_path / "empty_reader_file.txt"
    file_path.touch()
    content = await file_reader_tool_instance.execute(mock_agent_context_file_ops, path=str(file_path))
    assert content == ""

@pytest.mark.asyncio
async def test_read_io_error_functional(tmp_path, mocker, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops: AgentContext):
    file_path_str = str(tmp_path / "reader_io_error_file.txt")
    with open(file_path_str, 'w') as f: f.write("content") 

    original_open = open 
    def mock_open_for_reader(path_arg, *args, **kwargs):
        if path_arg == file_path_str: 
            raise IOError("Simulated open error for read_file")
        return original_open(path_arg, *args, **kwargs) 
    
    mocker.patch('autobyteus.tools.file.read_file.open', side_effect=mock_open_for_reader)
    
    with pytest.raises(IOError, match=f"Could not read file at {file_path_str}: Simulated open error for read_file"):
        await file_reader_tool_instance.execute(mock_agent_context_file_ops, path=file_path_str)
