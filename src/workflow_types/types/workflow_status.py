from enum import Enum

class WorkflowStatus(Enum):
    """
    Enumeration representing the status of a workflow.
    Possible statuses are 'Success', 'Started', and 'Failure'.
    """
    Success = 'Success'
    Started = 'Started'
    Failure = 'Failure'