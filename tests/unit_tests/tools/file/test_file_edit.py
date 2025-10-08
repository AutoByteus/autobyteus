import pytest
from unittest.mock import Mock

import autobyteus.tools.file.file_editor  # Ensure registration side-effects

from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.file.file_editor import PatchApplicationError

TOOL_NAME_FILE_EDIT = "FileEdit"

@pytest.fixture
def mock_agent_context_file_ops():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_file_ops_func_edit"
    mock_context.workspace = None
    return mock_context

@pytest.fixture
def file_edit_tool_instance(mock_agent_context_file_ops) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_FILE_EDIT)
    assert isinstance(tool_instance, BaseTool)
    tool_instance.set_agent_id(mock_agent_context_file_ops.agent_id)
    return tool_instance


def test_file_edit_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_FILE_EDIT)
    assert definition is not None
    assert definition.name == TOOL_NAME_FILE_EDIT
    assert "Applies a unified diff patch" in definition.description

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 3

    path_param = schema.get_parameter("path")
    assert isinstance(path_param, ParameterDefinition)
    assert path_param.param_type == ParameterType.STRING
    assert path_param.required is True

    patch_param = schema.get_parameter("patch")
    assert isinstance(patch_param, ParameterDefinition)
    assert patch_param.param_type == ParameterType.STRING
    assert patch_param.required is True

    create_param = schema.get_parameter("create_if_missing")
    assert isinstance(create_param, ParameterDefinition)
    assert create_param.param_type == ParameterType.BOOLEAN
    assert create_param.required is False

@pytest.mark.asyncio
async def test_apply_patch_to_existing_file(file_edit_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("line1\nline2\nline3\n", encoding='utf-8')

    patch = """@@ -1,3 +1,3 @@
 line1
-line2
+line2 updated
 line3
"""

    result = await file_edit_tool_instance.execute(
        mock_agent_context_file_ops,
        path=str(file_path),
        patch=patch,
    )

    assert result == f"File edited successfully at {file_path}"
    assert file_path.read_text(encoding='utf-8') == "line1\nline2 updated\nline3\n"

@pytest.mark.asyncio
async def test_patch_failure_raises_error(file_edit_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    file_path = tmp_path / "sample_failure.txt"
    file_path.write_text("alpha\nbeta\ngamma\n", encoding='utf-8')

    patch = """@@ -1,3 +1,3 @@
 alpha
-delta
+theta
 gamma
"""

    with pytest.raises(PatchApplicationError):
        await file_edit_tool_instance.execute(
            mock_agent_context_file_ops,
            path=str(file_path),
            patch=patch,
        )

@pytest.mark.asyncio
async def test_create_new_file_via_patch(file_edit_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    target_path = tmp_path / "newdir" / "created.txt"

    patch = """@@ -0,0 +1,2 @@
+hello
+world
"""

    result = await file_edit_tool_instance.execute(
        mock_agent_context_file_ops,
        path=str(target_path),
        patch=patch,
        create_if_missing=True,
    )

    assert result == f"File edited successfully at {target_path}"
    assert target_path.read_text(encoding='utf-8') == "hello\nworld\n"

@pytest.mark.asyncio
async def test_missing_file_without_create_flag(file_edit_tool_instance: BaseTool, mock_agent_context_file_ops, tmp_path):
    target_path = tmp_path / "nonexistent.txt"
    patch = """@@ -0,0 +1,1 @@
+content
"""

    with pytest.raises(FileNotFoundError):
        await file_edit_tool_instance.execute(
            mock_agent_context_file_ops,
            path=str(target_path),
            patch=patch,
        )
