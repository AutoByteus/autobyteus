# autobyteus/workspaces/errors/workspace_already_exists_error.py
"""
This module contains an exception class for handling the case 
where an attempt is made to add a workspace that already exists.
"""


class WorkspaceAlreadyExistsError(Exception):
    """
    An exception raised when trying to add a workspace that already exists.
    """
    pass
