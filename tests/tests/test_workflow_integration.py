import sys
import pytest

from unittest.mock import MagicMock
from llm_workflow_core.registry.workflow_registry import WorkflowRegistry
from automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow

# Test: Register and load the AutomatedCodingWorkflow using WorkflowRegistry
def test_given_workflow_registry_when_registering_and_loading_automated_coding_workflow_then_workflow_is_registered_and_loaded_correctly():
    # Given: A WorkflowRegistry instance
    registry = WorkflowRegistry()

    # When: Registering the AutomatedCodingWorkflow
    workflow_package = "automated_coding_workflow"

    # When: Loading the workflow using the WorkflowRegistry
    config = {"workflows": {"enabled_workflows": [workflow_package]}}
    registry.load_enabled_workflows(config)


    # Then: The workflow is loaded correctly
    assert registry.get_workflow_class(workflow_package) == AutomatedCodingWorkflow
