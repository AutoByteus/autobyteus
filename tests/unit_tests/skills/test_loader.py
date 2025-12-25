import os
import pytest
import shutil
import tempfile
from autobyteus.skills.loader import SkillLoader

class TestSkillLoader:
    @pytest.fixture
    def temp_skill_dir(self):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)

    def test_load_valid_skill(self, temp_skill_dir):
        skill_content = """---
name: test_skill
description: A skill for testing
---
# Content
This is the skill body.
"""
        with open(os.path.join(temp_skill_dir, "SKILL.md"), "w") as f:
            f.write(skill_content)

        skill = SkillLoader.load_skill(temp_skill_dir)
        
        assert skill.name == "test_skill"
        assert skill.description == "A skill for testing"
        assert skill.content == "# Content\nThis is the skill body."
        assert skill.root_path == temp_skill_dir

    def test_load_skill_forgiving_format(self, temp_skill_dir):
        # Testing with extra spaces, weird casing, and no leading newline
        skill_content = """  ---  
NAME:  flexible_skill  
Description:   A very flexible description  
---
Body starts here.
"""
        with open(os.path.join(temp_skill_dir, "SKILL.md"), "w") as f:
            f.write(skill_content)

        skill = SkillLoader.load_skill(temp_skill_dir)
        
        assert skill.name == "flexible_skill"
        assert skill.description == "A very flexible description"
        assert skill.content == "Body starts here."

    def test_load_skill_missing_file(self, temp_skill_dir):
        with pytest.raises(FileNotFoundError):
            SkillLoader.load_skill(temp_skill_dir)

    def test_load_skill_invalid_format(self, temp_skill_dir):
        # Missing opening ---
        skill_content = "name: invalid\ndescription: missing dashes\n---\ncontent"
        with open(os.path.join(temp_skill_dir, "SKILL.md"), "w") as f:
            f.write(skill_content)

        with pytest.raises(ValueError, match="Could not find frontmatter block"):
            SkillLoader.load_skill(temp_skill_dir)

    def test_load_skill_missing_metadata(self, temp_skill_dir):
        # Missing description
        skill_content = "---\nname: incomplete\n---\ncontent"
        with open(os.path.join(temp_skill_dir, "SKILL.md"), "w") as f:
            f.write(skill_content)

        with pytest.raises(ValueError, match="Missing 'description'"):
            SkillLoader.load_skill(temp_skill_dir)

