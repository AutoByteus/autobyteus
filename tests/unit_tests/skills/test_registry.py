import os
import pytest
import shutil
import tempfile
from autobyteus.skills.registry import SkillRegistry

class TestSkillRegistry:
    @pytest.fixture(autouse=True)
    def clear_registry(self):
        # Ensure registry is clean before and after each test
        SkillRegistry().clear()
        yield
        SkillRegistry().clear()

    @pytest.fixture
    def temp_base_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_singleton_behavior(self):
        registry1 = SkillRegistry()
        registry2 = SkillRegistry()
        assert registry1 is registry2

    def test_register_skill_from_path(self, temp_base_dir):
        skill_path = os.path.join(temp_base_dir, "my_skill")
        os.makedirs(skill_path)
        with open(os.path.join(skill_path, "SKILL.md"), "w") as f:
            f.write("---\nname: my_skill\ndescription: test\n---\ncontent")

        registry = SkillRegistry()
        skill = registry.register_skill_from_path(skill_path)
        
        assert skill.name == "my_skill"
        assert registry.get_skill("my_skill") is skill
        assert len(registry.list_skills()) == 1

    def test_discover_skills(self, temp_base_dir):
        # Create multiple skills
        for name in ["skill1", "skill2"]:
            path = os.path.join(temp_base_dir, name)
            os.makedirs(path)
            with open(os.path.join(path, "SKILL.md"), "w") as f:
                f.write(f"---\nname: {name}\ndescription: desc for {name}\n---\ncontent")

        # Create a non-skill directory
        os.makedirs(os.path.join(temp_base_dir, "not_a_skill"))

        registry = SkillRegistry()
        registry.discover_skills(temp_base_dir)
        
        assert len(registry.list_skills()) == 2
        assert registry.get_skill("skill1") is not None
        assert registry.get_skill("skill2") is not None
        assert registry.get_skill("not_a_skill") is None
