# file: autobyteus/autobyteus/agent/message/send_message_to.py
import logging
from typing import TYPE_CHECKING, Any, Optional

from ...tools.base_tool import BaseTool
from ...tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
# This import is for type hinting only and avoids circular dependencies at runtime
if TYPE_CHECKING:
    from ..context import AgentContext
    from ..workflow.context.team_manager import TeamManager
    from ..workflow.events.workflow_events import PostInterAgentMessageRequestEvent

logger = logging.getLogger(__name__)

class SendMessageTo(BaseTool):
    """
    A tool for sending messages to other agents within the same workflow team.
    This tool requires a TeamManager to be injected at runtime by the
    workflow framework to enable communication with the parent orchestrator.
    """
    TOOL_NAME = "SendMessageTo"

    def __init__(self, team_manager: Optional['TeamManager'] = None):
        """
        Initializes the SendMessageTo tool.

        Args:
            team_manager: An optional TeamManager instance. This is
                          typically injected by the TeamManager itself at agent creation.
        """
        self._team_manager = team_manager
        logger.debug(f"SendMessageTo tool initialized. TeamManager injected: {self._team_manager is not None}")

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
        Creates and dispatches a PostInterAgentMessageRequestEvent to the parent workflow
        using the injected team_manager.
        """
        # Local import to break circular dependency at module load time.
        from ..workflow.events.workflow_events import PostInterAgentMessageRequestEvent

        if self._team_manager is None:
            error_msg = "Critical error: SendMessageTo tool is not configured for workflow communication. It can only be used within a managed AgenticWorkflow."
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

        # Create the event for the workflow to handle
        event = PostInterAgentMessageRequestEvent(
            sender_agent_id=sender_agent_id,
            recipient_name=recipient_name,
            content=content,
            message_type=message_type
        )
        
        # Dispatch the event "up" to the workflow's event loop via the team manager
        await self._team_manager.dispatch_inter_agent_message_request(event)

        success_msg = f"Message dispatch for recipient '{recipient_name}' has been successfully requested."
        logger.info(f"Tool '{self.get_name()}': {success_msg}")
        return success_msg
