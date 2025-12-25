import os
import shutil
import tempfile
import pytest
from unittest.mock import Mock
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.skills.registry import SkillRegistry

class TestAgentSkillsIntegration:
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        SkillRegistry().clear()
        yield
        SkillRegistry().clear()

    @pytest.fixture
    def temp_skill_dir(self):
        temp_dir = tempfile.mkdtemp()
        skill_path = os.path.join(temp_dir, "java_expert")
        os.makedirs(skill_path)
        with open(os.path.join(skill_path, "SKILL.md"), "w") as f:
            f.write("---\nname: java_expert\ndescription: Java expert\n---\nJava Map Body")
            
        yield skill_path
        shutil.rmtree(temp_dir)

    def test_agent_with_preloaded_skill_path(self, temp_skill_dir):
        # 1. Setup Mock LLM
        mock_llm = Mock(spec=BaseLLM)
        
        # 2. Create Config with Skill Path
        config = AgentConfig(
            name="TestAgent",
            role="Tester",
            description="Testing skills",
            llm_instance=mock_llm,
            skills=[temp_skill_dir]
        )
        
        # 3. Create Agent via Factory
        factory = AgentFactory()
        agent = factory.create_agent(config)
        
        # 4. Verify System Prompt Injection
        # We manually run the processors that would normally be run during agent startup/processing
        context = agent.context
        processors = context.config.system_prompt_processors
        
        system_prompt = "Initial prompt"
        for processor in processors:
            system_prompt = processor.process(system_prompt, {}, agent.agent_id, context)
            
        assert "## Agent Skills" in system_prompt
        assert "Preloaded Skills" in system_prompt
        assert "Java Map Body" in system_prompt
        assert f'path="{temp_skill_dir}"' in system_prompt
        # Also verify the skill name was resolved
        assert "java_expert" in context.config.skills

    def test_agent_with_available_skill_discovery(self, temp_skill_dir):
        # 1. Register skill in registry first (simulating discovery)
        registry = SkillRegistry()
        registry.register_skill_from_path(temp_skill_dir)
        
        # 2. Create Agent without preloaded skills
        mock_llm = Mock(spec=BaseLLM)
        config = AgentConfig(
            name="Generalist",
            role="Assistant",
            description="No preloaded skills",
            llm_instance=mock_llm,
            skills=[]
        )
        
        factory = AgentFactory()
        agent = factory.create_agent(config)
        
        # 3. Verify Awareness in System Prompt
        context = agent.context
        system_prompt = "Initial"
        for processor in context.config.system_prompt_processors:
            system_prompt = processor.process(system_prompt, {}, agent.agent_id, context)
            
        assert "Available Skills" in system_prompt
        assert "- java_expert: Java expert" in system_prompt
        assert "Java Map Body" not in system_prompt # Content should NOT be there
