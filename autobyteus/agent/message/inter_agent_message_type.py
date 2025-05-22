from autobyteus.utils.dynamic_enum import DynamicEnum

class InterAgentMessageType(DynamicEnum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    TASK_COMPLETED = "task_completed"
    CLARIFICATION = "clarification"
    ERROR = "error"

    @classmethod
    def add_type(cls, name: str, value: str) -> 'InterAgentMessageType': # Updated return type hint
        """
        Add a new inter-agent message type dynamically.

        Args:
            name (str): The name of the new message type.
            value (str): The value of the new message type.

        Returns:
            InterAgentMessageType: The newly created InterAgentMessageType. # Updated return type in docstring

        Raises:
            ValueError: If the name or value already exists.
        """
        try:
            return cls.add(name, value)
        except ValueError as e:
            # Consider logging a warning here if a logger is available and appropriate
            # For now, print as in original code
            print(f"Warning: Failed to add new inter-agent message type. {str(e)}")
            return None
