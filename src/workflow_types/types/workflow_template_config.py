"""
src/workflow_template_config.py

This module contains the type definitions for the workflow configuration templates.
"""

from typing import TypedDict, Dict


class StepsTemplateConfig(TypedDict, total=False):
    step_class: type
    steps: Dict[str, 'StepsTemplateConfig']


class WorkflowTemplateStepsConfig(TypedDict, total=False):
    workspace_path: str
    steps: Dict[str, StepsTemplateConfig]
