# file: autobyteus/agent/group/send_message_to.py
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.group.message_types import Message, MessageType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autobyteus.agent.group.base_agent_orchestrator import BaseAgentOrchestrator

class SendMessageTo(BaseTool):
    def __init__(self, orchestrator: 'BaseAgentOrchestrator'):
        super().__init__()
        self.orchestrator = orchestrator

    async def _execute(self, recipient_role_name: str, recipient_agent_id: str, content: str, message_type: str, sender_agent_id: str) -> Any:
        try:
            msg_type = MessageType[message_type.upper()]
        except KeyError:
            return f"Error: Invalid message type '{message_type}'. Valid types are: {', '.join([t.name for t in MessageType])}"

        message = Message(recipient_role_name, recipient_agent_id, content, msg_type, sender_agent_id)
        return await self.orchestrator.route_message(message)

    def tool_usage(self) -> str:
        return self.tool_usage_xml()

    def tool_usage_xml(self) -> str:
        return '''SendMessageTo: Sends a message to another agent in the group. Usage:
    <command name="SendMessageTo">
      <arg name="recipient_role_name">GeneralRoleName</arg>
      <arg name="recipient_agent_id">SpecificAgentId or "unknown"</arg>
      <arg name="content">Your message here</arg>
      <arg name="message_type">TASK_ASSIGNMENT|TASK_RESULT|TASK_COMPLETED|CLARIFICATION|ERROR</arg>
      <arg name="sender_agent_id">YourSpecificAgentId</arg>
    </command>
    where:
    - "recipient_role_name" is the general role name of the recipient agent
    - "recipient_agent_id" is the specific ID of the recipient agent, or "unknown" if not known
    - "content" is the actual message text
    - "message_type" is one of: TASK_ASSIGNMENT, TASK_RESULT, TASK_COMPLETED, CLARIFICATION, or ERROR
    - "sender_agent_id" is the specific ID of the sender agent
    Example:
    <command name="SendMessageTo">
      <arg name="recipient_role_name">worker</arg>
      <arg name="recipient_agent_id">worker_001</arg>
      <arg name="content">Please provide more details about the task output.</arg>
      <arg name="message_type">CLARIFICATION</arg>
      <arg name="sender_agent_id">coordinator_001</arg>
    </command>
    '''