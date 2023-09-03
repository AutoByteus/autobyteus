# autobyteus/workspaces/project_type_determiner/project_type_determiner.py

import os

from autobyteus.workspaces.setting.project_types import ProjectType

class ProjectTypeDeterminer:
    """
    Class to determine the type of a project.
    """

    PROJECT_TYPE_FILES = {
        "requirements.txt": ProjectType.PYTHON,
        "build.gradle": ProjectType.JAVA,
        "package.json": ProjectType.NODEJS
    }

    def determine(self, workspace_root_path: str) -> ProjectType:
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
            ProjectType: The type of the project, one of the ProjectType enum values.
        """
        for file_name in os.listdir(workspace_root_path):
            if file_name in self.PROJECT_TYPE_FILES:
                return self.PROJECT_TYPE_FILES[file_name]

        # Default to 'unknown' if no specific project type can be determined
        return ProjectType.UNKNOWN
