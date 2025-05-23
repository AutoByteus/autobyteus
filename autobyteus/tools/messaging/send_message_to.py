import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.agent.message.inter_agent_message import InterAgentMessage # Still needed
from autobyteus.agent.group.agent_group_context import AgentGroupContext 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.agent import Agent

logger = logging.getLogger(__name__)

@tool(name="SendMessageTo") # Keep registered name
async def send_message_to( # function name can be send_message_to
    context: 'AgentContext',
    recipient_role_name: str,
    content: str,
    message_type: str,
    recipient_agent_id: Optional[str] = None
) -> str:
    """
    Sends a message to another agent within the same group.
    'recipient_role_name' is the role of the target agent.
    'content' is the message text.
    'message_type' defines the message's purpose (e.g., TASK_ASSIGNMENT).
    'recipient_agent_id' (optional) specifies a direct target agent ID.
    Requires 'agent_group_context' to be present in agent's context.custom_data.
    """
    sender_agent_id = context.agent_id
    tool_name_str = "SendMessageTo" 
    logger.info(f"Functional Tool '{tool_name_str}': Sender '{sender_agent_id}' sending message. "
                f"Role: '{recipient_role_name}', ID: '{recipient_agent_id}', Type: '{message_type}'.")

    group_context_any = context.custom_data.get('agent_group_context')
    if not isinstance(group_context_any, AgentGroupContext):
        error_msg = f"Tool '{tool_name_str}' critical error: AgentGroupContext not found for agent '{sender_agent_id}'."
        logger.error(error_msg)
        return f"Error: {error_msg}"
    
    group_context: AgentGroupContext = group_context_any
    target_agent: Optional['Agent'] = None

    if recipient_agent_id and recipient_agent_id.lower() != "unknown" and recipient_agent_id.strip() != "":
        target_agent = group_context.get_agent(recipient_agent_id)
        if not target_agent:
            logger.warning(f"Tool '{tool_name_str}': Agent ID '{recipient_agent_id}' not found in group '{group_context.group_id}'. Trying role '{recipient_role_name}'.")
    
    if not target_agent:
        if not recipient_role_name or recipient_role_name.strip() == "":
            error_msg = "Both recipient_agent_id and recipient_role_name are missing or invalid."
            logger.error(f"Tool '{tool_name_str}': {error_msg}")
            return f"Error: {error_msg}"

        agents_with_role = group_context.get_agents_by_role(recipient_role_name)
        if not agents_with_role:
            error_msg = f"No agent found for role '{recipient_role_name}' or ID '{recipient_agent_id}' in group '{group_context.group_id}'."
            logger.error(f"Tool '{tool_name_str}': {error_msg}")
            return f"Error: {error_msg}"
        if len(agents_with_role) > 1:
            logger.warning(f"Tool '{tool_name_str}': Multiple agents for role '{recipient_role_name}'. Sending to first: {agents_with_role[0].agent_id}.")
        target_agent = agents_with_role[0]

    if not target_agent:
        error_msg = f"Could not resolve recipient for role '{recipient_role_name}' or ID '{recipient_agent_id}'."
        logger.error(f"Tool '{tool_name_str}': {error_msg}")
        return f"Error: {error_msg}"

    try:
        message_to_send = InterAgentMessage.create_with_dynamic_message_type(
            recipient_role_name=target_agent.context.definition.role,
            recipient_agent_id=target_agent.agent_id,
            content=content,
            message_type=message_type,
            sender_agent_id=sender_agent_id
        )
        await target_agent.post_inter_agent_message(message_to_send)
        success_msg = f"Message successfully sent from '{sender_agent_id}' to '{target_agent.agent_id}' (Role: '{target_agent.context.definition.role}')."
        logger.info(f"Tool '{tool_name_str}': {success_msg}")
        return success_msg
    except ValueError as ve:
        error_msg = f"Error creating message: {str(ve)}"
        logger.error(f"Tool '{tool_name_str}': {error_msg}", exc_info=True)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error sending message: {str(e)}"
        logger.error(f"Tool '{tool_name_str}': {error_msg}", exc_info=True)
        return f"Error: {error_msg}"
