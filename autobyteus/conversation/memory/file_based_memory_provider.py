from autobyteus.conversation.memory import MemoryProvider

class FileBasedMemoryProvider(MemoryProvider):
    def __init__(self, conversation_id: str):
        self.file_path = conversation_id

    def store_conversation(self, role, message):
        with open(self.file_path, "a") as f:
            f.write(f"{role}: {message}\n")

    def get_conversation_history(self):
        with open(self.file_path, "r") as f:
            return [line.strip() for line in f.readlines()]
