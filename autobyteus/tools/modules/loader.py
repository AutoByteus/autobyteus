from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from autobyteus.tools.registry import ToolDefinition, default_tool_registry
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.utils.parameter_schema import ParameterSchema

from .filesystem_module_tool import FilesystemModuleTool
from .module_manifest import ModuleManifest
from .schema_builder import build_argument_schema

logger = logging.getLogger(__name__)


def _build_definition(manifest: ModuleManifest) -> ToolDefinition:
    def argument_schema_provider() -> ParameterSchema:
        return build_argument_schema(manifest)

    def config_schema_provider() -> None:
        return None

    def factory(config=None):
        return FilesystemModuleTool(manifest=manifest, config=config)

    return ToolDefinition(
        name=manifest.name,
        description=manifest.description,
        origin=ToolOrigin.LOCAL,
        category=manifest.category,
        argument_schema_provider=argument_schema_provider,
        config_schema_provider=config_schema_provider,
        custom_factory=factory,
        metadata=manifest.to_metadata(),
    )


def _register_manifest(manifest: ModuleManifest) -> str:
    definition = _build_definition(manifest)
    default_tool_registry.register_tool(definition)
    logger.info("Registered filesystem module '%s'", manifest.name)
    return manifest.name


def _instantiate_tools(tool_names: List[str]) -> Dict[str, FilesystemModuleTool]:
    instances = {}
    for name in tool_names:
        try:
            tool_instance = default_tool_registry.create_tool(name)
            instances[name] = tool_instance
        except Exception as exc:
            logger.error("Failed to instantiate module tool '%s': %s", name, exc)
    return instances


def load_filesystem_module_tools(manifest_paths: List[str]) -> Dict[str, FilesystemModuleTool]:
    tool_names: List[str] = []
    for raw_path in manifest_paths:
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if path.is_dir():
            candidate = path / "module.json"
        else:
            candidate = path
        if not candidate.exists():
            logger.error("Module manifest '%s' not found.", candidate)
            continue
        try:
            manifest = ModuleManifest.from_json_file(candidate)
        except Exception as exc:
            logger.error("Failed to parse module manifest '%s': %s", candidate, exc)
            continue
        tool_names.append(_register_manifest(manifest))

    return _instantiate_tools(tool_names)
