import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Stub optional dependency 'pathspec' used by autobyteus.tools; only minimal surface needed for import.
class _DummyPathSpec:
    @staticmethod
    def from_lines(pattern_cls, lines):
        class _Spec:
            def match_file(self, path):
                return False
        return _Spec()

_pathspec_stub = types.SimpleNamespace(
    PathSpec=_DummyPathSpec,
    patterns=types.SimpleNamespace(GitWildMatchPattern=object)
)
sys.modules.setdefault("pathspec", _pathspec_stub)
sys.modules.setdefault("pathspec.patterns", _pathspec_stub.patterns)

# Stub optional dependency 'google.genai' used by multimedia image tooling.
google_stub = types.SimpleNamespace(genai=MagicMock())
sys.modules.setdefault("google", google_stub)
sys.modules.setdefault("google.genai", google_stub.genai)

# Stub 'openai' dependency used by multimedia image tooling.
sys.modules.setdefault("openai", MagicMock())

# Stub 'aiohttp' dependency; will be monkeypatched in tests.
class _StubAiohttp:
    class ClientError(Exception):
        pass
    class ClientSession:
        def __init__(self, *args, **kwargs):
            pass

sys.modules.setdefault("aiohttp", _StubAiohttp())

from autobyteus.tools.multimedia import download_media_tool
from autobyteus.tools.multimedia.download_media_tool import DownloadMediaTool


# --- Dummy HTTP layer to avoid real network calls ---
class _DummyContent:
    async def iter_chunked(self, size: int):
        yield b"test-bytes"


class _DummyResponse:
    def __init__(self, headers: dict):
        self.headers = headers
        self.content = _DummyContent()

    def raise_for_status(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySession:
    def __init__(self, headers: dict):
        self._headers = headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str, timeout: int):
        return _DummyResponse(self._headers)


@pytest.mark.asyncio
async def test_relative_folder_resolves_inside_workspace(monkeypatch, tmp_path):
    tool = DownloadMediaTool()

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    mock_workspace = MagicMock()
    mock_workspace.get_base_path.return_value = str(workspace_root)

    context = MagicMock()
    context.agent_id = "agent-1"
    context.workspace = mock_workspace

    # Fake HTTP client
    monkeypatch.setattr(download_media_tool.aiohttp, "ClientSession", lambda: _DummySession({"Content-Type": "audio/wav"}))

    result = await tool.execute(
        context=context,
        url="http://example.com/audio.wav",
        filename="sample-audio",
        folder="relative/folder"
    )

    saved_path = Path(result.replace("Successfully downloaded file to: ", "").strip())
    assert saved_path.exists()
    assert saved_path.parent == workspace_root / "relative" / "folder"
    assert saved_path.suffix == ".wav"


@pytest.mark.asyncio
async def test_relative_folder_falls_back_to_default_download(monkeypatch, tmp_path):
    tool = DownloadMediaTool()

    default_root = tmp_path / "downloads"
    monkeypatch.setattr(download_media_tool, "get_default_download_folder", lambda: str(default_root))

    context = MagicMock()
    context.agent_id = "agent-2"
    context.workspace = None

    monkeypatch.setattr(download_media_tool.aiohttp, "ClientSession", lambda: _DummySession({"Content-Type": "application/pdf"}))

    result = await tool.execute(
        context=context,
        url="http://example.com/file.pdf",
        filename="doc",
        folder="reports"
    )

    saved_path = Path(result.replace("Successfully downloaded file to: ", "").strip())
    assert saved_path.exists()
    assert saved_path.parent == default_root / "reports"
    assert saved_path.suffix == ".pdf"
