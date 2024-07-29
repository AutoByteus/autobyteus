from typing import TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.group.agent_group import AgentGroup

class SendMessageTo(BaseTool):
    def __init__(self, agent_group: 'AgentGroup'):
        super().__init__()
        self.agent_group = agent_group

    async def _execute(self, to_role: str, message: str, from_role: str) -> Any:
        return await self.agent_group.route_message(from_role, to_role, message)

    def tool_usage(self) -> str:
        return "SendMessageTo: Send a message to another agent. Usage: <<<SendMessageTo(to_role='target_role', message='Your message here', from_role='your_role')>>>"

    def tool_usage_xml(self) -> str:
        return '''
        <command name="SendMessageTo">
            <arg name="to_role">target_role</arg>
            <arg name="message">Your message here</arg>
            <arg name="from_role">your_role</arg>
        </command>
        '''