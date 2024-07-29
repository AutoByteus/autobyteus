# File: autobyteus/tools/send_message_to.py

from autobyteus.agent.agent_group import AgentGroup
from autobyteus.tools.base_tool import BaseTool

class SendMessageTo(BaseTool):
    def __init__(self, agent_group: AgentGroup):
        super().__init__()
        self.agent_group = agent_group

    async def _execute(self, to_role: str, message: str, from_role: str):
        return await self.agent_group.route_message(from_role, to_role, message)

    def tool_usage(self):
        return "SendMessageTo: Send a message to another agent. Usage: <<<SendMessageTo(to_role='target_role', message='Your message here', from_role='your_role')>>>"

    def tool_usage_xml(self):
        return '''
        <command name="SendMessageTo">
            <arg name="to_role">target_role</arg>
            <arg name="message">Your message here</arg>
            <arg name="from_role">your_role</arg>
        </command>
        '''