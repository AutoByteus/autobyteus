from abc import ABC, abstractmethod

class PersistenceProvider(ABC):
    @abstractmethod
    def __init__(self, conversation_name):
        pass
    
    @abstractmethod
    def store_conversation(self, role, message):
        pass

    @abstractmethod
    def get_conversation_history(self):
        pass