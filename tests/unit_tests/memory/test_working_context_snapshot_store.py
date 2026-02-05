from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


def test_working_context_snapshot_store_read_write_exists(tmp_path):
    store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id="agent_1")

    assert not store.exists("agent_1")

    payload = {"schema_version": 1, "agent_id": "agent_1", "messages": []}
    store.write("agent_1", payload)

    assert store.exists("agent_1")
    loaded = store.read("agent_1")
    assert loaded == payload
