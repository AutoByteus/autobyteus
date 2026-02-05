import json
from pathlib import Path
from typing import Optional, Union, Dict, Any


class WorkingContextSnapshotStore:
    def __init__(self, base_dir: Union[str, Path], agent_id: str) -> None:
        self.base_dir = Path(base_dir)
        self.agent_id = agent_id

    def exists(self, agent_id: str) -> bool:
        return self._get_path(agent_id).exists()

    def read(self, agent_id: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(agent_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write(self, agent_id: str, payload: Dict[str, Any]) -> None:
        path = self._get_path(agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def _get_path(self, agent_id: str) -> Path:
        return self.base_dir / "agents" / agent_id / "working_context_snapshot.json"
