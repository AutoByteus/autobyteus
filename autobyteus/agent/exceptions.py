# File: autobyteus/exceptions.py

class AgentNotFoundException(Exception):
    def __init__(self, agent_id: str):
        super().__init__(f"Agent with id {agent_id} not found. This is an invalid state.")
        self.agent_id = agent_id