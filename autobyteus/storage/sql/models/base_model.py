from repository_sqlalchemy import Base
from sqlalchemy import Column, DateTime, Integer, func
class BaseModel(Base):
    """
    BaseModel is a foundational model class that encapsulates common 
    attributes and behaviors for all derived models.
    
    Attributes:
        id: The primary key for the model.
        created_at: The datetime when the record was created.
        updated_at: The datetime when the record was last updated.
    """
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
