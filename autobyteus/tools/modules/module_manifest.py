from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModuleArgument:
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    item_type: Optional[str] = None


@dataclass
class ModuleManifest:
    name: str
    description: str
    command: List[str]
    working_dir: Path
    category: str = "filesystem"
    arguments: List[ModuleArgument] = field(default_factory=list)
    timeout_seconds: Optional[float] = 120.0
    env: Dict[str, str] = field(default_factory=dict)
    manifest_path: Optional[Path] = None

    @classmethod
    def from_json_file(cls, path: Path) -> "ModuleManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        arguments = [ModuleArgument(**entry) for entry in data.get("arguments", [])]
        working_dir = path.parent / data.get("working_dir", ".")
        command = data["command"]
        if isinstance(command, str):
            command = [command]
        return cls(
            name=data["name"],
            description=data.get("description", data["name"]),
            command=command,
            working_dir=working_dir.resolve(),
            category=data.get("category", "filesystem"),
            arguments=arguments,
            timeout_seconds=data.get("timeout_seconds", 120.0),
            env=data.get("env", {}),
            manifest_path=path.resolve(),
        )

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "category": self.category,
        }
