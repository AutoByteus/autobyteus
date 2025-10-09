import os
from pathlib import Path
from typing import Any, Dict

import pytest

from autobyteus.clients.autobyteus_client import AutobyteusClient


class DummyClient:
    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        self.kwargs = kwargs

    async def aclose(self) -> None:
        return None

    def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def restore_env():
    original = os.environ.copy()
    os.environ["AUTOBYTEUS_API_KEY"] = "test-key"
    yield
    os.environ.clear()
    os.environ.update(original)


def test_missing_api_key_raises_value_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AUTOBYTEUS_API_KEY", raising=False)
    with pytest.raises(ValueError):
        AutobyteusClient(server_url="https://example.com")


def test_server_url_override(monkeypatch: pytest.MonkeyPatch):
    os.environ["AUTOBYTEUS_LLM_SERVER_URL"] = "https://env-host"

    captured: Dict[str, Any] = {}

    def fake_async_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["async"] = kwargs
        return DummyClient(**kwargs)

    def fake_sync_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["sync"] = kwargs
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("httpx.Client", fake_sync_client)

    client = AutobyteusClient(server_url="https://override-host")
    assert client.server_url == "https://override-host"

    assert captured["async"]["verify"] is False
    assert captured["sync"]["verify"] is False


def test_custom_cert_path_enables_verification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("dummy")

    os.environ["AUTOBYTEUS_SSL_CERT_FILE"] = str(cert_path)

    captured: Dict[str, Any] = {}

    def fake_async_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["async"] = kwargs
        return DummyClient(**kwargs)

    def fake_sync_client(**kwargs: Dict[str, Any]) -> DummyClient:
        captured["sync"] = kwargs
        return DummyClient(**kwargs)

    monkeypatch.setattr("httpx.AsyncClient", fake_async_client)
    monkeypatch.setattr("httpx.Client", fake_sync_client)

    AutobyteusClient()
    assert captured["async"]["verify"] == str(cert_path)
    assert captured["sync"]["verify"] == str(cert_path)


@pytest.mark.asyncio
async def test_async_context_manager(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("httpx.AsyncClient", lambda **_: DummyClient())
    monkeypatch.setattr("httpx.Client", lambda **_: DummyClient())

    async with AutobyteusClient() as client:
        assert isinstance(client, AutobyteusClient)
