# file: autobyteus/agent/message/send_message_to.py
import logging
from typing import TYPE_CHECKING, Any, Optional

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig
# This import is for type hinting only and avoids circular dependencies at runtime
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.context.team_manager import TeamManager
    from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent

logger = logging.getLogger(__name__)

class SendMessageTo(BaseTool):
    """
    A tool for sending messages to other agents within the same agent team.
    This tool dynamically retrieves the team communication channel from the
    agent's context at runtime.
    """
    TOOL_NAME = "SendMessageTo"
    CATEGORY = ToolCategory.AGENT_COMMUNICATION

    def __init__(self, config: Optional[ToolConfig] = None):
        """
        Initializes the stateless SendMessageTo tool.
        """
        super().__init__(config=config)
        # The TeamManager is no longer stored as an instance variable.
        logger.debug("SendMessageTo tool initialized (stateless).")

    # The set_team_manager method has been removed.

    @classmethod
    def get_name(cls) -> str:
        return cls.TOOL_NAME

    @classmethod
    def get_description(cls) -> str:
        return ("Sends a message to another agent within the same team, starting them if necessary. "
                "You must specify the recipient by their unique name as provided in your team manifest.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="recipient_name",
            param_type=ParameterType.STRING,
            description='The unique name of the recipient agent (e.g., "Researcher", "Writer_1"). This MUST match a name from your team manifest.',
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="content",
            param_type=ParameterType.STRING,
            description="The actual message content or task instruction.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="message_type",
            param_type=ParameterType.STRING,
            description="Type of the message (e.g., TASK_ASSIGNMENT, CLARIFICATION). Custom types allowed.",
            required=True
        ))
        return schema

    async def _execute(self, 
                       context: 'AgentContext', 
                       recipient_name: str, 
                       content: str, 
                       message_type: str) -> str:
        """
        Creates and dispatches an InterAgentMessageRequestEvent to the parent agent team
        by retrieving the TeamManager from the agent's context.
        """
        # Local import to break circular dependency at module load time.
        from autobyteus.agent_team.events.agent_team_events import InterAgentMessageRequestEvent

        # --- NEW: Retrieve TeamManager dynamically from context ---
        team_context: Optional['AgentTeamContext'] = context.custom_data.get("team_context")
        if not team_context:
            error_msg = "Critical error: SendMessageTo tool is not configured for team communication. It can only be used within a managed AgentTeam."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return f"Error: {error_msg}"
        
        team_manager: Optional['TeamManager'] = team_context.team_manager
        if not team_manager:
            # This is an internal framework error and should not happen in a correctly configured team.
            error_msg = "Internal Error: TeamManager not found in the provided team_context."
            logger.error(f"Agent '{context.agent_id}': {error_msg}")
            return f"Error: {error_msg}"

        # --- Input Validation ---
        if not isinstance(recipient_name, str) or not recipient_name.strip():
            error_msg = "Error: `recipient_name` must be a non-empty string."
            logger.error(f"Tool '{self.get_name()}' validation failed: {error_msg}")
            return error_msg
        if not isinstance(content, str) or not content.strip():
            error_msg = "Error: `content` must be a non-empty string."
            logger.error(f"Tool '{self.get_name()}' validation failed: {error_msg}")
            return error_msg
        if not isinstance(message_type, str) or not message_type.strip():
            error_msg = "Error: `message_type` must be a non-empty string."
            logger.error(f"Tool '{self.get_name()}' validation failed: {error_msg}")
            return error_msg
            
        sender_agent_id = context.agent_id
        logger.info(f"Tool '{self.get_name()}': Agent '{sender_agent_id}' requesting to send message to '{recipient_name}'.")

        # Create the event for the agent team to handle
        event = InterAgentMessageRequestEvent(
            sender_agent_id=sender_agent_id,
            recipient_name=recipient_name,
            content=content,
            message_type=message_type
        )
        
        # Dispatch the event "up" to the team's event loop via the dynamically retrieved team manager
        await team_manager.dispatch_inter_agent_message_request(event)

        success_msg = f"Message dispatch for recipient '{recipient_name}' has been successfully requested."
        logger.info(f"Tool '{self.get_name()}': {success_msg}")
        return success_msg