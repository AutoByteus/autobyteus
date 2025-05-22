# file: autobyteus/agent/message/send_message_to.py
import logging
from typing import TYPE_CHECKING, Any, Optional

from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.group.agent_group_context import AgentGroupContext # For type hint

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
    TOOL_NAME = "SendMessageTo"

    def __init__(self):
        """
        Initializes the SendMessageTo tool.
        The orchestrator is no longer injected; communication relies on AgentContext.
        """
        super().__init__()
        logger.debug(f"{self.TOOL_NAME} tool initialized.")

    def get_name(self) -> str:
        return self.TOOL_NAME

    async def _execute(self, 
                       context: 'AgentContext', 
                       recipient_role_name: str, 
                       content: str, 
                       message_type: str, 
                       recipient_agent_id: Optional[str] = None) -> Any:
        """
        Sends a message to another agent in the group.

        Args:
            context: The AgentContext of the calling agent.
            recipient_role_name: The role name of the intended recipient agent.
            content: The content of the message.
            message_type: The type of the message (e.g., TASK_ASSIGNMENT, CLARIFICATION).
                          This will be dynamically converted to InterAgentMessageType.
            recipient_agent_id: Optional. The specific ID of the recipient agent.
                                If "unknown" or not provided, the system will try to find an agent
                                by role (recipient_role_name).

        Returns:
            A string indicating success or failure.
        """
        sender_agent_id = context.agent_id
        logger.info(f"Tool '{self.TOOL_NAME}': Sender '{sender_agent_id}' attempting to send message. "
                    f"Recipient Role: '{recipient_role_name}', Recipient ID: '{recipient_agent_id}', Type: '{message_type}'.")

        group_context: Optional[AgentGroupContext] = context.custom_data.get('agent_group_context') # type: ignore
        
        if not isinstance(group_context, AgentGroupContext):
            error_msg = f"Tool '{self.TOOL_NAME}' critical error: AgentGroupContext not found in AgentContext.custom_data for agent '{sender_agent_id}'. Cannot send message."
            logger.error(error_msg)
            return f"Error: {error_msg}"

        target_agent: Optional['Agent'] = None

        if recipient_agent_id and recipient_agent_id.lower() != "unknown":
            target_agent = group_context.get_agent(recipient_agent_id)
            if not target_agent:
                logger.warning(f"Tool '{self.TOOL_NAME}': Agent with ID '{recipient_agent_id}' not found in group '{group_context.group_id}'. "
                               f"Attempting to find by role '{recipient_role_name}'.")
        
        if not target_agent: # If ID not provided, "unknown", or not found by ID
            agents_with_role = group_context.get_agents_by_role(recipient_role_name)
            if not agents_with_role:
                error_msg = f"No agent found with role '{recipient_role_name}' (and specific ID '{recipient_agent_id}' if provided was not found) in group '{group_context.group_id}'."
                logger.error(f"Tool '{self.TOOL_NAME}': {error_msg}")
                return f"Error: {error_msg}"
            
            if len(agents_with_role) > 1:
                logger.warning(f"Tool '{self.TOOL_NAME}': Multiple agents ({len(agents_with_role)}) found for role '{recipient_role_name}'. "
                               f"Sending to the first one: {agents_with_role[0].agent_id}. "
                               "Consider using specific recipient_agent_id for clarity.")
            target_agent = agents_with_role[0]
            # Update recipient_agent_id if it was resolved by role
            recipient_agent_id = target_agent.agent_id


        if not target_agent: # Should be captured above, but as a final check
            error_msg = f"Could not resolve recipient agent with role '{recipient_role_name}' or ID '{recipient_agent_id}'."
            logger.error(f"Tool '{self.TOOL_NAME}': {error_msg}")
            return f"Error: {error_msg}"

        try:
            # recipient_agent_id is now guaranteed to be the specific ID of the target_agent
            message_to_send = InterAgentMessage.create_with_dynamic_message_type(
                recipient_role_name=target_agent.context.definition.role, # Use actual role of resolved agent
                recipient_agent_id=target_agent.agent_id,
                content=content,
                message_type=message_type,
                sender_agent_id=sender_agent_id
            )
            
            await target_agent.post_inter_agent_message(message_to_send)
            success_msg = (f"Message successfully sent from '{sender_agent_id}' to agent "
                           f"'{target_agent.agent_id}' (Role: '{target_agent.context.definition.role}').")
            logger.info(f"Tool '{self.TOOL_NAME}': {success_msg}")
            return success_msg
        except ValueError as ve: # From InterAgentMessage.create_with_dynamic_message_type for invalid message_type
            error_msg = f"Error creating message: {str(ve)}"
            logger.error(f"Tool '{self.TOOL_NAME}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"An unexpected error occurred while sending message: {str(e)}"
            logger.error(f"Tool '{self.TOOL_NAME}': {error_msg}", exc_info=True)
            return f"Error: {error_msg}"
    
    def tool_usage_xml(self) -> str:
        # FR33: Updated tool_usage_xml
        return f'''<{self.TOOL_NAME}>: Sends a message to another agent in the same group.
    Usage:
    <command name="{self.TOOL_NAME}">
      <arg name="recipient_role_name">GeneralRoleName</arg>
      <arg name="content">Your message here</arg>
      <arg name="message_type">TASK_ASSIGNMENT|TASK_RESULT|CLARIFICATION|ERROR|custom_type</arg>
      <arg name="recipient_agent_id">OptionalSpecificAgentId</arg> <!-- Optional -->
    </command>
    Where:
    - "recipient_role_name" (string, required): The general role name of the recipient agent (e.g., "worker", "reviewer").
    - "content" (string, required): The actual message text.
    - "message_type" (string, required): The type of the message. Common types include TASK_ASSIGNMENT, TASK_RESULT, CLARIFICATION, ERROR. Custom types can also be used.
    - "recipient_agent_id" (string, optional): The specific ID of the recipient agent.
        - If provided and valid, the message is sent directly to this agent.
        - If omitted, "unknown", or if the ID is not found, the system attempts to deliver the message to an agent matching "recipient_role_name". If multiple agents match the role, one will be chosen (typically the first found). For precise delivery, use the agent ID.
    The sender's agent ID is automatically determined from the context.
    Example 1 (to a specific worker):
    <command name="{self.TOOL_NAME}">
      <arg name="recipient_role_name">worker_translator</arg>
      <arg name="recipient_agent_id">translator_agent_alpha</arg>
      <arg name="content">Please translate the following text to French: Hello World.</arg>
      <arg name="message_type">TASK_ASSIGNMENT</arg>
    </command>
    Example 2 (to any agent with role 'analyst'):
    <command name="{self.TOOL_NAME}">
      <arg name="recipient_role_name">analyst</arg>
      <arg name="content">Can you provide an analysis of the recent sales data?</arg>
      <arg name="message_type">TASK_ASSIGNMENT</arg>
    </command>
    '''
