# file: autobyteus/autobyteus/agent_team/exceptions.py

class TeamNodeNotFoundException(Exception):
    """Raised when a node (agent or sub-team) cannot be found in the agent team."""
    def __init__(self, node_name: str, team_id: str):
        super().__init__(f"Node '{node_name}' not found in agent team '{team_id}'.")
        self.node_name = node_name
        self.team_id = team_id
