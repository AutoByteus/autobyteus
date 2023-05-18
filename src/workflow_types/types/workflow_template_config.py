"""
workflow_template_config.py
This module contains the type definitions for the workflow configuration templates.
"""

from __future__ import annotations
from typing import TypedDict, Dict, Type, Union


class StageTemplateConfig(TypedDict, total=False):
    stage_class: type
    stages: Dict[str, 'StageTemplateConfig']


class WorkflowTemplateStagesConfig(TypedDict, total=False):
    workspace_path: str
    stages: Dict[str, StageTemplateConfig]
