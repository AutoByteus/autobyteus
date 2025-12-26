import pytest
import os
import shutil
import tempfile
from unittest.mock import Mock
from autobyteus.tools.registry import default_tool_registry 
from autobyteus.tools.base_tool import BaseTool 
from autobyteus.agent.context import AgentContext
from autobyteus.skills.registry import SkillRegistry

TOOL_NAME_LOAD_SKILL = "load_skill"

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_load_skill"
    return mock_context

@pytest.fixture
def load_skill_tool_instance(mock_agent_context: AgentContext) -> BaseTool:
    tool_instance = default_tool_registry.create_tool(TOOL_NAME_LOAD_SKILL)
    assert isinstance(tool_instance, BaseTool) 
    tool_instance.set_agent_id(mock_agent_context.agent_id)
    return tool_instance

@pytest.fixture(autouse=True)
def clear_skill_registry():
    SkillRegistry().clear()
    yield
    SkillRegistry().clear()

@pytest.fixture
def temp_skill_path():
    temp_dir = tempfile.mkdtemp()
    skill_path = os.path.join(temp_dir, "test_skill")
    os.makedirs(skill_path)
    with open(os.path.join(skill_path, "SKILL.md"), "w") as f:
        f.write("---\nname: test_skill\ndescription: A test skill\n---\nBody of the skill.")
    yield skill_path
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_load_skill_by_name(load_skill_tool_instance: BaseTool, mock_agent_context: AgentContext, temp_skill_path: str):
    # First, register it so it can be found by name
    registry = SkillRegistry()
    registry.register_skill_from_path(temp_skill_path)
    
    result = await load_skill_tool_instance.execute(mock_agent_context, skill_name="test_skill")
    
    assert "## Skill: test_skill" in result
    assert f"Root Path: {temp_skill_path}" in result
    assert "CRITICAL: Path Resolution" in result
    assert "Body of the skill." in result

@pytest.mark.asyncio
async def test_load_skill_by_path(load_skill_tool_instance: BaseTool, mock_agent_context: AgentContext, temp_skill_path: str):
    # Load directly by path without pre-registering
    result = await load_skill_tool_instance.execute(mock_agent_context, skill_name=temp_skill_path)
    
    assert "## Skill: test_skill" in result
    assert f"Root Path: {temp_skill_path}" in result
    assert "CRITICAL: Path Resolution" in result
    assert "Body of the skill." in result

@pytest.mark.asyncio
async def test_load_skill_not_found(load_skill_tool_instance: BaseTool, mock_agent_context: AgentContext):
    with pytest.raises(ValueError, match="Skill 'non_existent' not found"):
        await load_skill_tool_instance.execute(mock_agent_context, skill_name="non_existent")
