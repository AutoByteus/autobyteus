"""
File: tools/coordinator/backup_handler.py

Module for handling backups of files during transactional operations.

This module provides functionalities to create backups before file
operations and restore them if needed. The BackupHandler class interacts
with the BackupLogger to log backup activities.
"""

import os
import shutil


class BackupHandler:
    def _backup_filename(self, transaction_id: str, filepath: str) -> str:
        """Generate a backup filename based on transaction_id and original filename."""
        dir_name, file_name = os.path.split(filepath)
        backup_name = f"{transaction_id}_backup_{file_name}"
        return os.path.join(dir_name, backup_name)

    def create_backup(self, transaction_id: str, filepath: str) -> None:
        """
        Create a backup of the given file for the provided transaction_id.

        Args:
            transaction_id (str): The ID of the current transaction.
            filepath (str): Path to the file that needs to be backed up.
        """
        backup_path = self._backup_filename(transaction_id, filepath)
        shutil.copy2(filepath, backup_path)  # Copying file to its backup location.
        self.logger.log_backup_activity(f"Backup created for {filepath} at {backup_path}")

    def restore_backup(self, transaction_id: str, filepath: str) -> None:
        """
        Restore a file from its backup for the given transaction_id.

        Args:
            transaction_id (str): The ID of the current transaction.
            filepath (str): Path to the original file that needs to be restored.
        """
        backup_path = self._backup_filename(transaction_id, filepath)
        if os.path.exists(backup_path):
            shutil.move(backup_path, filepath)  # Restoring original file from backup.
            self.logger.log_backup_activity(f"Backup at {backup_path} restored to {filepath}")
        else:
            self.logger.log_backup_activity(f"No backup found for {filepath} for transaction {transaction_id}")
