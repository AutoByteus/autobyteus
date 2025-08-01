# file: autobyteus/autobyteus/workflow/exceptions.py

class WorkflowNodeNotFoundException(Exception):
    """Raised when a node (agent or sub-workflow) cannot be found in the workflow."""
    def __init__(self, node_name: str, workflow_id: str):
        super().__init__(f"Node '{node_name}' not found in workflow '{workflow_id}'.")
        self.node_name = node_name
        self.workflow_id = workflow_id
