from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SkillDocument:
    """Represents a skill specification loaded from disk."""

    name: str
    content: str
    skill_path: Path
    skill_file: Path


def _discover_skill_file(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "skill.md"
    else:
        candidate = path

    if not candidate.exists():
        raise FileNotFoundError(f"Skill file '{candidate}' does not exist.")
    if not candidate.is_file():
        raise IsADirectoryError(f"Skill path '{candidate}' must reference a file.")
    return candidate


def _read_skill(path: Path) -> SkillDocument:
    skill_file = _discover_skill_file(path)
    skill_dir = skill_file.parent
    content = skill_file.read_text(encoding="utf-8").strip()
    pretty_name = skill_dir.name.replace("_", " ") or skill_file.stem
    return SkillDocument(
        name=pretty_name,
        content=content,
        skill_path=skill_dir,
        skill_file=skill_file,
    )


def load_skill_documents(skill_paths: List[str]) -> List[SkillDocument]:
    """Loads and normalizes a list of skill documents from disk."""

    documents: List[SkillDocument] = []
    for raw_path in skill_paths:
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        try:
            doc = _read_skill(path)
            documents.append(doc)
        except Exception as exc:
            logger.error("Failed to load skill file '%s': %s", path, exc)
    return documents
