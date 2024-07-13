import os
from datetime import datetime
from autobyteus.conversation.persistence.provider import PersistenceProvider

class FileBasedPersistenceProvider(PersistenceProvider):
    def __init__(self, conversation_name: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = ''.join(c if c.isalnum() else '_' for c in conversation_name)
        self.file_path = f"conversations/{safe_name}_{timestamp}.txt"
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        open(self.file_path, 'a').close()  # Create the file if it doesn't exist

    def store_conversation(self, role, message):
        with open(self.file_path, "a") as f:
            f.write(f"{role}: {message}\n")

    def get_conversation_history(self):
        with open(self.file_path, "r") as f:
            return [line.strip() for line in f.readlines()]