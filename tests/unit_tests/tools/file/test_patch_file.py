import pytest
from unittest.mock import Mock

import autobyteus.tools.file.patch_file  # Ensure registration side-effects
import autobyteus.tools.file.read_file

from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.file.patch_file import PatchApplicationError

TOOL_NAME_PATCH_FILE = "patch_file"

@pytest.fixture
def mock_agent_context_file_ops():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_file_ops_func_patch"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def file_patch_tool_instance(mock_agent_context_file_ops) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_PATCH_FILE)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context_file_ops.agent_id)
    return tool_instance


def test_file_patch_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_PATCH_FILE)
    assert definition is not None
    assert definition.name == TOOL_NAME_PATCH_FILE
    assert "Applies a unified diff patch" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 2

    path_param = schema.get_parameter("path")
    assert isinstance(path_param, ParameterDefinition)
    assert path_param.param_type == ParameterType.STRING
    assert path_param.required is True

    patch_param = schema.get_parameter("patch")
    assert isinstance(patch_param, ParameterDefinition)
    assert patch_param.param_type == ParameterType.STRING
    assert patch_param.required is True

@pytest.mark.asyncio
async def test_apply_patch_to_existing_file(file_patch_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("line1\nline2\nline3\n", encoding='utf-8')

    patch = """@@ -1,3 +1,3 @@
 line1
-line2
+line2 updated
 line3
"""

    result = await file_patch_tool_instance.execute(
        mock_agent_context_file_ops,
        path=str(file_path),
        patch=patch,
    )

    assert result == f"File patched successfully at {file_path}"
    assert file_path.read_text(encoding='utf-8') == "line1\nline2 updated\nline3\n"

@pytest.mark.asyncio
async def test_patch_failure_raises_error(file_patch_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    file_path = tmp_path / "sample_failure.txt"
    file_path.write_text("alpha\nbeta\ngamma\n", encoding='utf-8')

    patch = """@@ -1,3 +1,3 @@
 alpha
-delta
+theta
 gamma
"""

    with pytest.raises(PatchApplicationError):
        await file_patch_tool_instance.execute(
            mock_agent_context_file_ops,
            path=str(file_path),
            patch=patch,
        )

@pytest.mark.asyncio
async def test_missing_file_raises_error(file_patch_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    target_path = tmp_path / "nonexistent.txt"
    patch = """@@ -0,0 +1,1 @@
+content
"""

    with pytest.raises(FileNotFoundError):
        await file_patch_tool_instance.execute(
            mock_agent_context_file_ops,
            path=str(target_path),
            patch=patch,
        )

@pytest.fixture
def file_reader_tool_instance(mock_agent_context_file_ops) -> BaseTool:
    tool_instance = default_tool_registry.create_tool("read_file")
    tool_instance.set_agent_id(mock_agent_context_file_ops.agent_id)
    return tool_instance

@pytest.mark.asyncio
async def test_read_then_patch_flow(file_patch_tool_instance: BaseTool, file_reader_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    # 1. Setup file
    file_path = tmp_path / "flow_test.txt"
    file_path.write_text("line1\nline2\n", encoding='utf-8')
    
    # 2. Read file (Simulate LLM reading it)
    content = await file_reader_tool_instance.execute(
        mock_agent_context_file_ops, 
        path=str(file_path)
    )
    # Verify we got line numbers
    assert content == "1: line1\n2: line2\n"
    
    # 3. Patch file (LLM generates standard diff based on understanding)
    # Note: The patch itself uses clean context lines (standard unified diff format), 
    # effectively stripping the line numbers seen in the read step.
    patch = """@@ -1,2 +1,2 @@
 line1
-line2
+line2 modified
"""
    result = await file_patch_tool_instance.execute(
        mock_agent_context_file_ops,
        path=str(file_path),
        patch=patch
    )
    
    # 4. Verify
    assert result == f"File patched successfully at {file_path}"
    assert file_path.read_text(encoding='utf-8') == "line1\nline2 modified\n"
