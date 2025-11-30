from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional, Any, Dict

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig

from .module_manifest import ModuleManifest

logger = logging.getLogger(__name__)


class FilesystemModuleTool(BaseTool):
    """Executes a module command via stdin/stdout JSON protocol."""

    def __init__(self, manifest: ModuleManifest, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        self._manifest = manifest

    @classmethod
    def get_description(cls) -> str:
        return "Executes an external module command defined on the filesystem."

    @classmethod
    def get_argument_schema(cls):  # pragma: no cover
        return None

    def get_name(self) -> str:  # type: ignore[override]
        return self._manifest.name

    def get_description(self) -> str:  # type: ignore[override]
        return self._manifest.description

    def get_argument_schema(self):  # type: ignore[override]
        from .schema_builder import build_argument_schema
        return build_argument_schema(self._manifest)

    async def _execute(self, context, **kwargs) -> Any:  # type: ignore[override]
        payload = json.dumps({"args": kwargs}, ensure_ascii=False)
        env = os.environ.copy()
        env.update(self._manifest.env)

        process = await asyncio.create_subprocess_exec(
            *self._manifest.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self._manifest.working_dir),
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=payload.encode("utf-8")),
                timeout=self._manifest.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TimeoutError(
                f"Module '{self._manifest.name}' timed out after {self._manifest.timeout_seconds}s"
            ) from exc

        if process.returncode != 0:
            raise RuntimeError(
                f"Module '{self._manifest.name}' failed with code {process.returncode}: {stderr.decode('utf-8', errors='ignore')}"
            )

        output = stdout.decode("utf-8").strip()
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            logger.warning("Module '%s' returned non-JSON output: %s", self._manifest.name, output[:200])
            return output
