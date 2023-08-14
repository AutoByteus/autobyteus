# src/workspaces/project_type_determiner/project_type_determiner.py

import os

class ProjectTypeDeterminer:
    """
    Class to determine the type of a project.
    """
    def determine(self, workspace_root_path: str) -> str:
        """
        Determine the type of the project in the workspace.

        This method checks the root directory of the workspace for key files
        that indicate the project type. Specifically, it looks for:

        - 'requirements.txt' for Python projects
        - 'build.gradle' for Java projects
        - 'package.json' for Node.js projects

        If none of these files are found, the project type is set to 'unknown'.

        Args:
            workspace_root_path (str): The root path of the workspace.

        Returns:
            str: The type of the project ('python', 'java', 'nodejs', or 'unknown').
        """
        for file_name in os.listdir(workspace_root_path):
            if file_name == 'requirements.txt':
                return 'python'
            elif file_name == 'build.gradle':
                return 'java'
            elif file_name == 'package.json':
                return 'nodejs'

        # Default to 'unknown' if no specific project type can be determined
        return 'unknown'
