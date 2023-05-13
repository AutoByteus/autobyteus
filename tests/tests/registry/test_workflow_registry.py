import pytest
from unittest.mock import patch, MagicMock, create_autospec
from llm_workflow_core.registry.workflow_registry import WorkflowRegistry
from llm_workflow_core.types.base_workflow import BaseWorkflow
from llm_workflow_core.types.workflow_template_config import WorkflowTemplateStagesConfig

@pytest.fixture
def registry():
    return WorkflowRegistry()

def test_loading_enabled_workflows_with_valid_configuration_loads_correct_workflows(registry):
    config = {"workflows": {"enabled_workflows": ["test_workflow"]}}

    with patch("importlib.import_module") as mock_import_module:
        mock_module = MagicMock()
        mock_workflow_class = create_autospec(BaseWorkflow, instance=True)
        mock_workflow_config = create_autospec(WorkflowTemplateStagesConfig, instance=True)

        mock_module.WORKFLOW_CONFIG = {
            "workflow_class": mock_workflow_class,
            "workflow_config": mock_workflow_config,
        }
        mock_import_module.return_value = mock_module

        registry.load_enabled_workflows(config)

        assert registry.get_workflow_class("test_workflow") == mock_workflow_class
        assert registry.get_workflow_config("test_workflow") is mock_module.WORKFLOW_CONFIG

