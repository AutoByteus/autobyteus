import os
from pathlib import Path
from typing import Mapping, Optional, Union


def resolve_memory_base_dir(
    override_dir: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    fallback_dir: Optional[Union[str, Path]] = None,
) -> str:
    override_value = override_dir.strip() if override_dir else ""
    if override_value:
        return override_value

    env_values = env if env is not None else os.environ
    env_value = env_values.get("AUTOBYTEUS_MEMORY_DIR", "").strip()
    if env_value:
        return env_value

    if fallback_dir is not None:
        return str(fallback_dir)

    return str(Path.cwd() / "memory")


def resolve_agent_memory_dir(base_dir: Union[str, Path], agent_id: str) -> str:
    return str(Path(base_dir) / "agents" / agent_id)
