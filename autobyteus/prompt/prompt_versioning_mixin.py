from typing import Optional
from abc import abstractmethod

from autobyteus.storage.sql.models.prompt_version_model import PromptVersionModel
from autobyteus.storage.sql.repositories.prompt_version_repository import PromptVersionRepository

class PromptVersioningMixin:
    """
    A mixin to offer versioning functionalities and handle default prompts for entities
    interfacing with Large Language Models (LLMs).
    """
    
    default_prompt: str  # To be defined by classes that mix this in
    current_prompt: str  # The in-memory cached value of the current effective prompt
    
    @property
    @abstractmethod
    def prompt_name(self) -> str:
        """
        Abstract property that mandates implementing classes to provide a unique identifier 
        for their prompts.
        """
        pass

    def __init__(self):
        self.current_prompt = self.get_current_effective_prompt()  # Initialize current_prompt from the database
        self.repository: PromptVersionRepository = PromptVersionRepository()

    def add_version(self, prompt: str) -> None:
        """
        Creates and stores a new version of the prompt. If the number of versions surpasses 
        the limit (4), it deletes the oldest version.
        """
        # Get the latest version number
        latest_version = self.repository.get_latest_created_version(prompt_name=self.prompt_name)
        
        # Determine the new version number
        version_no = latest_version.version_no + 1 if latest_version else 1
        
        # If adding this version exceeds the limit of 4, delete the oldest version
        if version_no > 4:
            self.repository.delete_oldest_version(prompt_name=self.prompt_name)
            # Shift down other versions
            for i in range(2, 5):
                version = self.repository.get_version(prompt_name=self.prompt_name, version_no=i)
                version.version_no -= 1
                self.repository.create_version(version)
        
        # Create the new version
        self.repository.create_version(PromptVersionModel(prompt_name=self.prompt_name, 
                                                          version_no=version_no, 
                                                          prompt_content=prompt, 
                                                          is_current_effective=False))

    def get_version(self, version_no: int) -> Optional[str]:
        """
        Retrieves the content of a specified prompt version.
        """
        version = self.repository.get_version(prompt_name=self.prompt_name, version_no=version_no)
        return version.prompt_content if version else None

    def set_current_effective_version(self, version_no: int) -> None:
        """
        Sets a specific version as the current effective prompt.
        """
        version = self.repository.get_version(prompt_name=self.prompt_name, version_no=version_no)
        if version:
            # Mark the specified version as the current effective version
            version.is_current_effective = True
            self.repository.create_version(version)
            # Update the in-memory cached value
            self.current_prompt = version.prompt_content

    def get_current_effective_prompt(self) -> str:
        """
        Fetches the content of the current effective prompt or initializes it with 
        the default if none exists.
        """
        if self.current_prompt:
            return self.current_prompt
        
        effective_version = self.repository.get_current_effective_version(prompt_name=self.prompt_name)
        if not effective_version:
            # If no effective version exists, initialize with default prompt
            self.add_version(self.default_prompt)
            return self.default_prompt
        
        return effective_version.prompt_content

    def load_latest_version(self) -> str:
        """
        Retrieves the content of the latest created prompt version.
        """
        latest_version = self.repository.get_latest_created_version(prompt_name=self.prompt_name)
        return latest_version.prompt_content if latest_version else self.default_prompt


