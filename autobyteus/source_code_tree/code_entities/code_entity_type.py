"""
File: autobyteus/source_code_tree/code_entities/code_entity_type.py

This module defines the CodeEntityType enum which represents the types of code entities.
"""

from enum import Enum


class CodeEntityType(Enum):
    CLASS = "class"
    MODULE = "module"
    METHOD = "method"
    FUNCTION = "function"
