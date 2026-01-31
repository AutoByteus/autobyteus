import json
from pathlib import Path
from typing import Iterable, List, Optional, Union

from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.store.base_store import MemoryStore


class FileMemoryStore(MemoryStore):
    def __init__(self, base_dir: Union[str, Path], agent_id: str):
        self.base_dir = Path(base_dir)
        self.agent_id = agent_id
        self.agent_dir = self.base_dir / "agents" / agent_id
        self.agent_dir.mkdir(parents=True, exist_ok=True)

    def add(self, items: Iterable[object]) -> None:
        for item in items:
            memory_type = getattr(item, "memory_type", None)
            if memory_type is None:
                raise ValueError("Memory item missing memory_type")
            path = self._get_file_path(memory_type)
            record = item.to_dict() if hasattr(item, "to_dict") else item
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")

    def list(self, memory_type: MemoryType, limit: Optional[int] = None) -> List[object]:
        path = self._get_file_path(memory_type)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle.readlines() if line.strip()]
        if limit is not None:
            lines = lines[-limit:]
        return [self._deserialize(memory_type, json.loads(line)) for line in lines]

    def list_raw_trace_dicts(self) -> List[dict]:
        path = self._get_file_path(MemoryType.RAW_TRACE)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def read_archive_raw_traces(self) -> List[dict]:
        path = self._get_archive_path()
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def prune_raw_traces(self, keep_turn_ids: set[str], archive: bool = True) -> None:
        raw_items = self.list_raw_trace_dicts()
        if not raw_items:
            return

        keep = []
        removed = []
        for item in raw_items:
            if item.get("turn_id") in keep_turn_ids:
                keep.append(item)
            else:
                removed.append(item)

        raw_path = self._get_file_path(MemoryType.RAW_TRACE)
        tmp_path = raw_path.with_suffix(".jsonl.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            for item in keep:
                handle.write(json.dumps(item) + "\n")
        tmp_path.replace(raw_path)

        if archive and removed:
            archive_path = self._get_archive_path()
            with archive_path.open("a", encoding="utf-8") as handle:
                for item in removed:
                    handle.write(json.dumps(item) + "\n")

    def _get_file_path(self, memory_type: MemoryType) -> Path:
        if memory_type == MemoryType.RAW_TRACE:
            return self.agent_dir / "raw_traces.jsonl"
        if memory_type == MemoryType.EPISODIC:
            return self.agent_dir / "episodic.jsonl"
        if memory_type == MemoryType.SEMANTIC:
            return self.agent_dir / "semantic.jsonl"
        raise ValueError(f"Unknown memory type: {memory_type}")

    def _deserialize(self, memory_type: MemoryType, data: dict) -> object:
        if memory_type == MemoryType.RAW_TRACE:
            return RawTraceItem.from_dict(data)
        if memory_type == MemoryType.EPISODIC:
            return EpisodicItem.from_dict(data)
        if memory_type == MemoryType.SEMANTIC:
            return SemanticItem.from_dict(data)
        raise ValueError(f"Unknown memory type: {memory_type}")

    def _get_archive_path(self) -> Path:
        return self.agent_dir / "raw_traces_archive.jsonl"
