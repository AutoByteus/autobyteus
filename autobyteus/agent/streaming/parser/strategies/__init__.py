"""
Detection strategies for streaming parser.
"""

from .base import DetectionStrategy
from .json_tool_strategy import JsonToolStrategy
from .sentinel_strategy import SentinelStrategy
from .xml_tag_strategy import XmlTagStrategy
from .registry import create_detection_strategies

__all__ = [
    "DetectionStrategy",
    "JsonToolStrategy",
    "SentinelStrategy",
    "XmlTagStrategy",
    "create_detection_strategies",
]
