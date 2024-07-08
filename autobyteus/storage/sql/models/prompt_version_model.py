"""
Module: autobyteus.storage.db.models.prompt_version_model

This module defines the PromptVersionModel, which represents the database model
for storing versioned prompts. Each entry contains the prompt identifier, version 
number, content of the prompt, whether the version is the current effective prompt,
and the creation/modification timestamp.
"""

from repository_sqlalchemy import Base
from sqlalchemy import Column, String, Integer, Text, Boolean

class PromptVersionModel(Base):
    """
    Represents the database model for storing versioned prompts.
    
    Attributes:
    - prompt_name (String): Identifier for the prompt.
    - version_no (Integer): Version number for the prompt.
    - prompt_content (Text): Content of the versioned prompt.
    - is_current_effective (Boolean): Indicates if this version is the current effective prompt.
    """
    
    __tablename__ = 'prompt_versions'
    
    prompt_name = Column(String, primary_key=True, nullable=False)
    version_no = Column(Integer, primary_key=True, nullable=False)
    prompt_content = Column(Text, nullable=False)
    is_current_effective = Column(Boolean, default=False, nullable=False)
