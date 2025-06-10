# file: autobyteus/autobyteus/agent/message/send_message_to.py
import logging
from typing import TYPE_CHECKING, Any, Optional

from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.group.agent_group_context import AgentGroupContext
# Updated imports for schema
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.agent import Agent 

logger = logging.getLogger(__name__)

class SendMessageTo(BaseTool):
    """
    A tool for sending messages to other agents within the same AgentGroup.
    It utilizes AgentGroupContext injected into the calling agent's AgentContext
    to resolve recipient agents.
    """
    TOOL_NAME = "SendMessageTo" # Class attribute for the name

    def __init__(self):
        super().__init__()
        logger.debug(f"{self.get_name()} tool initialized.") # Use get_name()

    @classmethod
    def get_name(cls) -> str: # Implemented as per BaseTool requirement
        return cls.TOOL_NAME

    @classmethod
    def get_description(cls) -> str:
        return ("Sends a message to another agent within the same group. "
                "Can target by role or specific agent ID.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="recipient_role_name",
            param_type=ParameterType.STRING,
            description="The general role name of the recipient agent (e.g., 'worker', 'reviewer').",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="content",
            param_type=ParameterType.STRING,
            description="The actual message text.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="message_type",
            param_type=ParameterType.STRING, # Or ENUM if InterAgentMessageType values are known and fixed for schema
            description="Type of the message (e.g., TASK_ASSIGNMENT, CLARIFICATION). Custom types allowed.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="recipient_agent_id",
            param_type=ParameterType.STRING,
            description='Optional. Specific ID of the recipient agent. If "unknown" or omitted, resolves by role.',
            required=False,
            default_value=None # Explicitly no default, truly optional
        ))
        return schema

    # tool_usage_xml() and tool_usage_json() are inherited from BaseTool
    # get_config_schema() for instantiation defaults to None

    async def _execute(self, 
                       context: 'AgentContext', 
                       recipient_role_name: str, 
                       content: str, 
                       message_type: str, 
                       recipient_agent_id: Optional[str] = None) -> str: # Named parameters
        """
        Sends a message to another agent in the group.
        Arguments are validated by BaseTool.execute().
        """
        sender_agent_id = context.agent_id
        logger.info(f"Tool '{self.get_name()}': Sender '{sender_agent_id}' attempting to send message. "
                    f"Recipient Role: '{recipient_role_name}', Recipient ID: '{recipient_agent_id}', Type: '{message_type}'.")

        group_context_any = context.custom_data.get('agent_group_context')
        
        if not isinstance(group_context_any, AgentGroupContext):
            error_msg = f"Tool '{self.get_name()}' critical error: AgentGroupContext not found or invalid in AgentContext.custom_data for agent '{sender_agent_id}'. Cannot send message."
            logger.error(error_msg)
            return f"Error: {error_msg}"
        
        group_context: AgentGroupContext = group_context_any # Type cast after check

        target_agent: Optional['Agent'] = None

        # Use recipient_agent_id if provided and not explicitly "unknown" (case-insensitive)
        if recipient_agent_id and recipient_agent_id.lower() != "unknown":
            target_agent = group_context.get_agent(recipient_agent_id)
            if not target_agent:
                logger.warning(f"Tool '{self.get_name()}': Agent with ID '{recipient_agent_id}' not found in group '{group_context.group_id}'. "
                               f"Attempting to find by role '{recipient_role_name}'.")
        
        if not target_agent: 
            agents_with_role = group_context.get_agents_by_role(recipient_role_name)
            if not agents_with_role:
                error_msg = f"No agent found with role '{recipient_role_name}' (and specific ID '{recipient_agent_id}' if provided was not found) in group '{group_context.group_id}'."
                logger.error(f"Tool '{self.get_name()}': {error_msg}")
                return f"Error: {error_msg}"
            
            if len(agents_with_role) > 1:
                logger.warning(f"Tool '{self.get_name()}': Multiple agents ({len(agents_with_role)}) found for role '{recipient_role_name}'. "
                               f"Sending to the first one: {agents_with_role[0].agent_id}. "
                               "Consider using specific recipient_agent_id for clarity.")
            target_agent = agents_with_role[0]
            # Update recipient_agent_id to the one resolved by role if it was initially None or "unknown"
            recipient_agent_id = target_agent.agent_id


        if not target_agent: 
            error_msg = f"Could not resolve recipient agent with role '{recipient_role_name}' or ID '{recipient_agent_id}'." # recipient_agent_id would be updated here
            logger.error(f"Tool '{self.get_name()}': {error_msg}")
            return f"Error: {error_msg}"

        try:
            message_to_send = InterAgentMessage.create_with_dynamic_message_type(
                recipient_role_name=target_agent.context.config.role, 
                recipient_agent_id=target_agent.agent_id, # Use the definitively resolved agent ID
                content=content,
                message_type=message_type,
                sender_agent_id=sender_agent_id
            )
            
            await target_agent.post_inter_agent_message(message_to_send)
            success_msg = (f"Message successfully sent from '{sender_agent_id}' to agent "
                           f"'{target_agent.agent_id}' (Role: '{target_agent.context.config.role}').")
            logger.info(f"Tool '{self.get_name()}': {success_msg}")
            return success_msg
        except ValueError as ve: 
            error_msg = f"Error creating message: {str(ve)}"
            logger.error(f"Tool '{self.get_name()}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"An unexpected error occurred while sending message: {str(e)}"
            logger.error(f"Tool '{self.get_name()}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"

    # tool_usage_xml was defined directly here, this is now inherited from BaseTool
    # BaseTool.tool_usage_xml() will use get_argument_schema() to generate it.
    # If a custom XML format was desired that differs from the auto-generated one,
    # then this method could be overridden. For now, assume auto-generated is fine.
