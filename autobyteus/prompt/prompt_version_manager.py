from typing import Optional
from autobyteus.prompt.storage.prompt_version_model import PromptVersionModel
from autobyteus.prompt.storage.prompt_version_repository import PromptVersionRepository

class PromptVersionManager:
    """
    A class to manage prompt versions for entities.
    """

    def __init__(self):
        self.repository: PromptVersionRepository = PromptVersionRepository()

    def add_version(self, prompt_name: str, prompt: str) -> None:
        """
        Creates and stores a new version of the prompt for an entity.
        """
        # Get the latest version number
        latest_version = self.repository.get_latest_created_version(prompt_name=prompt_name)

        # Determine the new version number
        version_no = latest_version.version_no + 1 if latest_version else 1

        # Create the new version
        self.repository.create_version(PromptVersionModel(prompt_name=prompt_name,
                                                          version_no=version_no,
                                                          prompt_content=prompt,
                                                          is_current_effective=False))

    def get_version(self, prompt_name: str, version_no: int) -> Optional[str]:
        """
        Retrieves the content of a specified prompt version for an entity.
        """
        version = self.repository.get_version(prompt_name=prompt_name, version_no=version_no)
        return version.prompt_content if version else None

    def set_current_effective_version(self, prompt_name: str, version_no: int) -> None:
        """
        Sets a specific version as the current effective prompt for an entity.
        """
        version = self.repository.get_version(prompt_name=prompt_name, version_no=version_no)
        if version:
            # Mark the specified version as the current effective version
            version.is_current_effective = True
            self.repository.create_version(version)

    def get_current_effective_version(self, prompt_name: str) -> Optional[int]:
        """
        Retrieves the version number of the current effective prompt for an entity.
        """
        effective_version = self.repository.get_current_effective_version(prompt_name=prompt_name)
        return effective_version.version_no if effective_version else None

    def load_latest_version(self, prompt_name: str) -> Optional[str]:
        """
        Retrieves the content of the latest created prompt version for an entity.
        """
        latest_version = self.repository.get_latest_created_version(prompt_name=prompt_name)
        return latest_version.prompt_content if latest_version else None