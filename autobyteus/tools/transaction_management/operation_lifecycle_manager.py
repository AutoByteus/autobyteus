"""
tools/coordinator/operation_lifecycle_manager.py

This module contains the OperationLifecycleManager class which manages the
transaction lifecycle including starting, committing, and rolling back transactions.
"""

import uuid
from autobyteus.tools.operation_executor.journal_manager import JournalManager
from autobyteus.tools.operation_executor.operation_event_producer import OperationEventProducer
from autobyteus.tools.transaction_management.backup_handler import BackupHandler
from tools.operation_executor.operation_executor import OperationExecutor
# Assuming the other required classes are located in their respective modules.

class OperationLifecycleManager:
    def __init__(self,
                 journal_manager: JournalManager,
                 operation_executor: OperationExecutor,
                 backup_handler: BackupHandler,
                 event_producer: OperationEventProducer) -> None:
        self.journal_manager = journal_manager
        self.operation_executor = operation_executor
        self.backup_handler = backup_handler
        self.event_producer = event_producer

    def start_transaction(self) -> str:
        """
        Initializes a transaction and returns a unique transaction ID.
        """
        transaction_id = str(uuid.uuid4())
        self.journal_manager.initialize_journal(transaction_id)
        return transaction_id

    def commit(self, transaction_id: str) -> None:
        """
        Commits all the operations, journals them, and emits an event indicating
        a successful commit.
        
        Args:
            transaction_id (str): The unique ID of the transaction to be committed.
        """
        try:
            self.journal_manager.finalize_journal(transaction_id, status="committed")
            self.event_producer.emit_event(f"Transaction {transaction_id} committed.")
        except Exception as e:
            self.journal_manager.log_error(transaction_id, str(e))
            raise

    def rollback(self, transaction_id: str) -> None:
        """
        Reverts all executed operations, restores files if necessary, and emits a rollback event.
        
        Args:
            transaction_id (str): The unique ID of the transaction to be rolled back.
        """
        try:
            self.operation_executor.rollback_operations()
            self.backup_handler.restore_backup(transaction_id)
            self.event_producer.emit_event(f"Transaction {transaction_id} rolled back.")
        except Exception as e:
            self.journal_manager.log_error(transaction_id, str(e))
            raise
