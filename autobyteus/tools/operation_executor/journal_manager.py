"""
File: tools/operation_executor/journal_manager.py

This module provides the JournalManager class that handles the journaling of operations for recovery purposes.
It works in collaboration with the OperationEventProducer to emit real-time events every time an operation is journaled.
"""
import os
import json
from datetime import datetime
from tools.operation.operation import Operation
from tools.operation_executor.operation_event_producer import OperationEventProducer

class JournalManager:
    """
    Manages the journaling of operations for recovery purposes.
    Collaborates with the OperationEventProducer to emit real-time events every time an operation is journaled.
    """

    def __init__(self, journal_path: str, event_producer: OperationEventProducer):
        """
        Initializes the JournalManager with a specified journal path and an event producer.

        Args:
            journal_path (str): The path where the journal files will be stored.
            event_producer (OperationEventProducer): The event producer to emit real-time events.
        """
        self.journal_path = journal_path
        self.event_producer = event_producer
        os.makedirs(journal_path, exist_ok=True)

    def initialize_journal(self, transaction_id: str, user: str = None, description: str = None) -> None:
        """
        Prepares the journal for a new transaction.

        Args:
            transaction_id (str): The unique identifier for the transaction.
            user (str): The user who initiated the transaction. Default is None.
            description (str): Description or purpose of the transaction. Default is None.
        """
        journal_file = os.path.join(self.journal_path, f"{transaction_id}.json")
        with open(journal_file, 'w') as file:
            data = {
                "transaction_id": transaction_id,
                "start_time": datetime.now().isoformat(),
                "user": user,
                "description": description,
                "operations": []
            }
            json.dump(data, file)
        self.event_producer.emit_event(f"Journal initialized for transaction {transaction_id}")


    def record_operation(self, operation: Operation) -> None:
        """
        Records a given operation in the journal.

        Args:
            operation (Operation): The operation to be recorded.
        """
        transaction_id = operation.transaction_id
        journal_file = os.path.join(self.journal_path, f"{transaction_id}.json")
        with open(journal_file, 'r+') as file:
            data = json.load(file)
            data["operations"].append(operation.to_dict())
            file.seek(0)
            json.dump(data, file)
        self.event_producer.emit_event(f"Operation {operation} recorded in journal for transaction {transaction_id}")

    def finalize_journal(self, transaction_id: str, status: str, error_message: str = None) -> None:
        """
        Marks the transaction as complete in the journal.

        Args:
            transaction_id (str): The unique identifier for the transaction.
            status (str): The final status of the transaction (e.g., "committed", "rolled_back").
            error_message (str): Any error message associated with the transaction's end. Default is None.
        """
        journal_file = os.path.join(self.journal_path, f"{transaction_id}.json")
        with open(journal_file, 'r+') as file:
            data = json.load(file)
            data["end_time"] = datetime.now().isoformat()
            data["status"] = status
            if error_message:
                data["error_message"] = error_message
            file.seek(0)
            json.dump(data, file)
        self.event_producer.emit_event(f"Journal finalized with status {status} for transaction {transaction_id}")


    def log_error(self, transaction_id: str, error_message: str) -> None:
        """
        Logs any errors encountered during the transaction's lifecycle.

        Args:
            transaction_id (str): The unique identifier for the transaction.
            error_message (str): The error message to be logged.
        """
        journal_file = os.path.join(self.journal_path, f"{transaction_id}.json")
        with open(journal_file, 'r+') as file:
            data = json.load(file)
            data.setdefault("errors", []).append({
                "error_message": error_message,
                "timestamp": datetime.now().isoformat()
            })
            file.seek(0)
            json.dump(data, file)
        self.event_producer.emit_event(f"Error logged for transaction {transaction_id}: {error_message}")
