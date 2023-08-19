"""
# tools/operation_executor/operation_executor.py
Module to handle the execution and potential reversion of operations.
"""

from typing import List
from tools.operation.operation import Operation
# Note: The below imports are placeholders, actual implementations would need to be linked.
# from journal_manager import JournalManager
# from operation_event_producer import OperationEventProducer

class OperationExecutor:
    """
    Manages the execution and potential reversion of operations.
    Interacts with the JournalManager and OperationEventProducer for logging and event emission.
    """
    
    def __init__(self):
        """
        Initializes the OperationExecutor with an empty operations list.
        """
        self.operations: List[Operation] = []
        # Assuming instances of JournalManager and OperationEventProducer are passed or instantiated here.
        # self.journal_manager = JournalManager()
        # self.event_producer = OperationEventProducer()
    
    def add_operation(self, operation: Operation):
        """
        Adds an operation to the list of operations to be executed.

        Args:
            operation (Operation): The operation to be added.
        """
        self.operations.append(operation)
        
    def execute_operations(self, transaction_id: str):
        """
        Executes all operations added to the executor. Logs and emits events for each operation.

        Args:
            transaction_id (str): The ID of the current transaction.
        """
        # self.journal_manager.initialize_journal(transaction_id)
        for operation in self.operations:
            operation.execute()
            # Log the operation and emit event
            # self.journal_manager.record_operation(operation)
            # self.event_producer.emit_event(f"Operation {operation} executed.")
            
    def rollback_operations(self):
        """
        Reverts all executed operations. This is done in reverse order to ensure the correct undoing of operations.
        """
        for operation in reversed(self.operations):
            operation.undo()
            # Emit event for rollback
            # self.event_producer.emit_event(f"Operation {operation} rolled back.")

