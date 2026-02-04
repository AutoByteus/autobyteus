from pathlib import Path

from autobyteus.memory.path_resolver import resolve_agent_memory_dir, resolve_memory_base_dir


def test_resolve_memory_base_dir_override_wins():
    resolved = resolve_memory_base_dir(
        override_dir=" /tmp/memory ",
        env={"AUTOBYTEUS_MEMORY_DIR": "/env/memory"},
        fallback_dir="/fallback/memory",
    )
    assert resolved == "/tmp/memory"


def test_resolve_memory_base_dir_env_used():
    resolved = resolve_memory_base_dir(env={"AUTOBYTEUS_MEMORY_DIR": " /env/memory "})
    assert resolved == "/env/memory"


def test_resolve_memory_base_dir_fallback_used():
    resolved = resolve_memory_base_dir(env={}, fallback_dir="/fallback/memory")
    assert resolved == "/fallback/memory"


def test_resolve_memory_base_dir_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = resolve_memory_base_dir(env={})
    assert resolved == str(tmp_path / "memory")


def test_resolve_agent_memory_dir():
    resolved = resolve_agent_memory_dir("/base", "agent_1")
    assert resolved == str(Path("/base") / "agents" / "agent_1")
