from typing import Optional
from autobyteus.db.models.prompt_version_model import PromptVersionModel
from autobyteus.db.repositories.base_repository import BaseRepository, ModelType


class PromptVersionRepository(BaseRepository):
    """
    A repository class that offers CRUD operations for PromptVersionModel and manages version-specific operations.
    This class interfaces with the database for operations related to prompt versions.
    """

    def create_version(self, prompt_version: PromptVersionModel) -> ModelType:
        """
        Store a new version of the prompt.

        Args:
            prompt_version (PromptVersionModel): The version to be stored.

        Returns:
            ModelType: The stored version.
        """
        return self.create(prompt_version)

    def get_version(self, prompt_name: str, version_no: int) -> Optional[PromptVersionModel]:
        """
        Retrieve a specific version of the prompt for a given name.

        Args:
            prompt_name (str): Identifier for the prompt.
            version_no (int): The version number to be retrieved.

        Returns:
            Optional[PromptVersionModel]: The retrieved version or None if not found.
        """
        with self.session_manager as session:
            return session.query(PromptVersionModel).filter_by(prompt_name=prompt_name, version_no=version_no).first()

    def get_current_effective_version(self, prompt_name: str) -> Optional[PromptVersionModel]:
        """
        Retrieve the current effective version of the prompt for a given name.

        Args:
            prompt_name (str): Identifier for the prompt.

        Returns:
            Optional[PromptVersionModel]: The current effective version or None if not found.
        """
        with self.session_manager as session:
            return session.query(PromptVersionModel).filter_by(prompt_name=prompt_name, is_current_effective=True).first()

    def get_latest_created_version(self, prompt_name: str) -> Optional[PromptVersionModel]:
        """
        Retrieve the most recently created version of the prompt for a given name.

        Args:
            prompt_name (str): Identifier for the prompt.

        Returns:
            Optional[PromptVersionModel]: The latest created version or None if not found.
        """
        with self.session_manager as session:
            return session.query(PromptVersionModel).filter_by(prompt_name=prompt_name).order_by(PromptVersionModel.created_at.desc()).first()

    def delete_version(self, prompt_name: str, version_no: int) -> None:
        """
        Delete a specific version of the prompt for a given name.

        Args:
            prompt_name (str): Identifier for the prompt.
            version_no (int): The version number to be deleted.
        """
        version = self.get_version(prompt_name, version_no)
        if version:
            self.delete(version)

    def delete_oldest_version(self, prompt_name: str) -> None:
        """
        Delete the oldest version of the prompt for a given name.

        Args:
            prompt_name (str): Identifier for the prompt.
        """
        with self.session_manager as session:
            oldest_version = session.query(PromptVersionModel).filter_by(prompt_name=prompt_name).order_by(PromptVersionModel.created_at.asc()).first()
            if oldest_version:
                self.delete(oldest_version)
