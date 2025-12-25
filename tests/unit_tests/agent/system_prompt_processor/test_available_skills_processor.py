import pytest
from unittest.mock import Mock
from autobyteus.agent.system_prompt_processor.available_skills_processor import AvailableSkillsProcessor
from autobyteus.skills.registry import SkillRegistry
from autobyteus.agent.context import AgentContext

class TestAvailableSkillsProcessor:
    @pytest.fixture(autouse=True)
    def clear_registry(self):
        SkillRegistry().clear()
        yield
        SkillRegistry().clear()

    @pytest.fixture
    def mock_context(self):
        mock_ctx = Mock(spec=AgentContext)
        mock_ctx.config = Mock()
        # Initial empty skills
        mock_ctx.config.skills = []
        return mock_ctx

    def test_process_no_skills(self, mock_context):
        processor = AvailableSkillsProcessor()
        prompt = "Original Prompt"
        result = processor.process(prompt, {}, "test_agent", mock_context)
        assert result == prompt

    def test_process_with_available_skill(self, mock_context):
        registry = SkillRegistry()
        # Manually register a skill by mocking the loader if needed, 
        # but easier to just use the Registry's internal dict for unit test
        from autobyteus.skills.model import Skill
        skill = Skill(name="test_skill", description="desc", content="body", root_path="/path")
        registry._skills["test_skill"] = skill
        
        processor = AvailableSkillsProcessor()
        result = processor.process("Original", {}, "test_agent", mock_context)
        
        assert "Original" in result
        assert "## Agent Skills" in result
        assert "Available Skills" in result
        assert "- test_skill: desc" in result
        assert "body" not in result

    def test_process_with_preloaded_skill(self, mock_context):
        registry = SkillRegistry()
        from autobyteus.skills.model import Skill
        skill = Skill(name="preloaded", description="desc", content="FULL_BODY", root_path="/path")
        registry._skills["preloaded"] = skill
        
        mock_context.config.skills = ["preloaded"]
        
        processor = AvailableSkillsProcessor()
        result = processor.process("Original", {}, "test_agent", mock_context)
        
        assert "Preloaded Skills" in result
        assert 'name="preloaded"' in result
        assert "FULL_BODY" in result
        assert "/path" in result
