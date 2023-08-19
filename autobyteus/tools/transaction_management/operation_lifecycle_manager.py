# tools/coordinator/operation_lifecycle_manager.py

"""
Module to manage the lifecycle of operations including the initiation, 
commitment, and rollback of transactions. It interacts with the TransactionLogger 
to log transaction activities.
"""

import uuid

class OperationLifecycleManager:
    """
    Manages the transaction lifecycle. Provides methods to start, commit, and rollback transactions.
    Interacts with the TransactionLogger to log transaction activities.
    """
    
    def __init__(self):
        """Initialize the OperationLifecycleManager."""
        self.logger = TransactionLogger()
    
    def start_transaction(self) -> str:
        """
        Start a new transaction and return a unique transaction ID.
        
        Returns:
            str: Unique transaction ID.
        """
        transaction_id = str(uuid.uuid4())
        self.logger.log_transaction_activity(f"Transaction {transaction_id} started.")
        return transaction_id
    
    def commit(self, transaction_id: str):
        """
        Commit the given transaction.
        
        Args:
            transaction_id (str): ID of the transaction to commit.
        """
        self.logger.log_transaction_activity(f"Transaction {transaction_id} committed.")
    
    def rollback(self, transaction_id: str):
        """
        Rollback the given transaction.
        
        Args:
            transaction_id (str): ID of the transaction to rollback.
        """
        self.logger.log_transaction_activity(f"Transaction {transaction_id} rolled back.")
