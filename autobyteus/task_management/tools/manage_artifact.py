# file: autobyteus/autobyteus/task_management/tools/manage_artifact.py
import datetime
import json
import logging
import uuid
from typing import TYPE_CHECKING, List, Optional

from pydantic import ValidationError

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.parameter_schema import (ParameterSchema,
                                               ParameterDefinition,
                                               ParameterType)
from autobyteus.task_management.artifacts import (ArtifactManifest,
                                                   ArtifactState, ArtifactType)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context import AgentTeamContext

logger = logging.getLogger(__name__)

class ManageArtifact(BaseTool):
    """A tool for agents to create and update ArtifactManifests in the team's shared registry."""

    CATEGORY = ToolCategory.TASK_MANAGEMENT

    @classmethod
    def get_name(cls) -> str:
        return "ManageArtifact"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Creates a new artifact or updates an existing one in the team's shared artifact registry. "
            "Artifacts are metadata pointers to work products like code or documents."
        )

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="artifact_id",
            param_type=ParameterType.STRING,
            description="The ID of the artifact to update. If omitted, a new artifact will be created.",
            required=False,
        ))
        schema.add_parameter(ParameterDefinition(
            name="name",
            param_type=ParameterType.STRING,
            description="The human-readable name of the artifact. Required when creating a new artifact.",
            required=False, # Required only if artifact_id is missing.
        ))
        schema.add_parameter(ParameterDefinition(
            name="description",
            param_type=ParameterType.STRING,
            description="A detailed description of the artifact's purpose and content.",
            required=False,
        ))
        schema.add_parameter(ParameterDefinition(
            name="artifact_type",
            param_type=ParameterType.ENUM,
            description=f"The type of artifact. Must be one of: {', '.join([t.value for t in ArtifactType])}. Required when creating.",
            required=False,
            enum_values=[t.value for t in ArtifactType],
        ))
        schema.add_parameter(ParameterDefinition(
            name="state",
            param_type=ParameterType.ENUM,
            description=f"The current state of the artifact. Must be one of: {', '.join([s.value for s in ArtifactState])}.",
            required=False,
            enum_values=[s.value for s in ArtifactState],
        ))
        schema.add_parameter(ParameterDefinition(
            name="file_manifest",
            param_type=ParameterType.ARRAY,
            description="A list of relative file paths that make up this artifact. The paths are relative to the team's shared workspace.",
            required=False,
            array_item_schema={"type": "string"}
        ))
        return schema

    async def _execute(self, context: 'AgentContext', **kwargs) -> str:
        """
        Executes the tool to manage an artifact.

        Note: This tool assumes `context.custom_data['team_context']` provides
        access to the `AgentTeamContext`.
        """
        agent_name = context.config.name
        logger.info(f"Agent '{agent_name}' is executing ManageArtifact with args: {kwargs}")

        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Error: Team context is not available. Cannot access the artifact registry."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg

        artifact_registry = getattr(team_context.state, 'artifact_registry', None)
        if artifact_registry is None:
            error_msg = "Error: Artifact registry has not been initialized for this team."
            logger.error(f"Agent '{agent_name}': {error_msg}")
            return error_msg

        artifact_id = kwargs.get("artifact_id")

        if artifact_id:
            # Update existing artifact
            if artifact_id not in artifact_registry:
                return f"Error: Artifact with ID '{artifact_id}' not found."
            
            artifact = artifact_registry[artifact_id]
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            update_data.pop("artifact_id", None) # Don't update the ID itself

            try:
                updated_artifact = artifact.model_copy(update=update_data)
                updated_artifact.mark_updated()
                artifact_registry[artifact_id] = updated_artifact
                msg = f"Successfully updated artifact '{updated_artifact.name}' (ID: {artifact_id})."
                logger.info(f"Agent '{agent_name}': {msg}")
                return msg
            except (ValidationError, TypeError) as e:
                error_msg = f"Failed to update artifact '{artifact_id}' due to invalid data: {e}"
                logger.warning(f"Agent '{agent_name}': {error_msg}")
                return f"Error: {error_msg}"
        else:
            # Create new artifact
            if "name" not in kwargs or "artifact_type" not in kwargs:
                return "Error: 'name' and 'artifact_type' are required to create a new artifact."

            try:
                new_id = f"art_{uuid.uuid4().hex[:12]}"
                manifest = ArtifactManifest(
                    artifact_id=new_id,
                    creator_agent_name=agent_name,
                    name=kwargs["name"],
                    description=kwargs.get("description"),
                    artifact_type=ArtifactType(kwargs["artifact_type"]),
                    state=ArtifactState(kwargs.get("state", "pending")),
                    file_manifest=kwargs.get("file_manifest", [])
                )
                artifact_registry[new_id] = manifest
                msg = f"Successfully created new artifact '{manifest.name}' with ID: {new_id}."
                logger.info(f"Agent '{agent_name}': {msg}")
                return msg
            except (ValidationError, ValueError, TypeError) as e:
                error_msg = f"Failed to create artifact due to invalid data: {e}"
                logger.warning(f"Agent '{agent_name}': {error_msg}")
                return f"Error: {error_msg}"
