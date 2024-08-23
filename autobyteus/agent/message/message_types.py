from autobyteus.utils.dynamic_enum import DynamicEnum

class MessageType(DynamicEnum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    TASK_COMPLETED = "task_completed"
    CLARIFICATION = "clarification"
    ERROR = "error"

    @classmethod
    def add_type(cls, name: str, value: str) -> 'MessageType':
        """
        Add a new message type dynamically.

        Args:
            name (str): The name of the new message type.
            value (str): The value of the new message type.

        Returns:
            MessageType: The newly created MessageType.

        Raises:
            ValueError: If the name or value already exists.
        """
        try:
            return cls.add(name, value)
        except ValueError as e:
            print(f"Warning: Failed to add new message type. {str(e)}")
            return None