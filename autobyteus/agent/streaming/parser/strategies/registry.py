"""
Registry for detection strategies.
"""
from __future__ import annotations

from typing import Dict, List

from .base import DetectionStrategy
from .json_tool_strategy import JsonToolStrategy
from .sentinel_strategy import SentinelStrategy
from .xml_tag_strategy import XmlTagStrategy


_STRATEGY_REGISTRY: Dict[str, DetectionStrategy] = {
    "sentinel": SentinelStrategy(),
    "xml_tag": XmlTagStrategy(),
    "json_tool": JsonToolStrategy(),
}


def create_detection_strategies(strategy_order: List[str]) -> List[DetectionStrategy]:
    """Create ordered detection strategies."""
    strategies: List[DetectionStrategy] = []
    for name in strategy_order:
        strategy = _STRATEGY_REGISTRY.get(name)
        if strategy:
            strategies.append(strategy)
    return strategies
