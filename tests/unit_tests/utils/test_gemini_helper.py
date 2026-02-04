from unittest.mock import MagicMock, patch

from autobyteus.utils.gemini_helper import initialize_gemini_client_with_runtime


def _clear_env(monkeypatch) -> None:
    for name in (
        "VERTEX_AI_API_KEY",
        "VERTEX_AI_PROJECT",
        "VERTEX_AI_LOCATION",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_initialize_prefers_vertex_api_key(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("VERTEX_AI_API_KEY", "vertex-key")
    monkeypatch.setenv("VERTEX_AI_PROJECT", "proj-123")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "us-central1")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

    fake_client = MagicMock()
    with patch("autobyteus.utils.gemini_helper.genai.Client", return_value=fake_client) as mock_client:
        client, runtime_info = initialize_gemini_client_with_runtime()

    assert client is fake_client
    mock_client.assert_called_once_with(vertexai=True, api_key="vertex-key")
    assert runtime_info.runtime == "vertex"
    assert runtime_info.project is None
    assert runtime_info.location is None


def test_initialize_vertex_project_location(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("VERTEX_AI_PROJECT", "proj-456")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "europe-west4")

    fake_client = MagicMock()
    with patch("autobyteus.utils.gemini_helper.genai.Client", return_value=fake_client) as mock_client:
        client, runtime_info = initialize_gemini_client_with_runtime()

    assert client is fake_client
    mock_client.assert_called_once_with(
        vertexai=True,
        project="proj-456",
        location="europe-west4",
    )
    assert runtime_info.runtime == "vertex"
    assert runtime_info.project == "proj-456"
    assert runtime_info.location == "europe-west4"


def test_initialize_gemini_api_key(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")

    fake_client = MagicMock()
    with patch("autobyteus.utils.gemini_helper.genai.Client", return_value=fake_client) as mock_client:
        client, runtime_info = initialize_gemini_client_with_runtime()

    assert client is fake_client
    mock_client.assert_called_once_with(api_key="gemini-key")
    assert runtime_info.runtime == "api_key"
    assert runtime_info.project is None
    assert runtime_info.location is None
