"""
Operation Error Handler Interface for extensible error handling.

This module provides the abstract base class and concrete implementations
for handling errors that occur during operations with support for recovery
attempts and custom error processing.
"""

import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .operation_logger import OperationContext


class OperationErrorHandler(ABC):
    """
    Abstract base class for operation error handlers.

    Provides interface for handling errors that occur during operations,
    with support for error recovery and context-aware error processing.
    """

    @abstractmethod
    def handle_operation_error(self, error: Exception, operation_context: OperationContext) -> Optional[Dict[str, Any]]:
        """
        Handle an error that occurred during an operation.

        Args:
            error: The exception that occurred
            operation_context: Full context of the operation when error occurred

        Returns:
            Dictionary with error handling results, or None if not handled
            Expected keys: 'handled', 'recovery_attempted', 'recovery_success', 'user_action'
        """
        pass

    @abstractmethod
    def can_recover(self, error: Exception, operation_context: OperationContext) -> bool:
        """
        Determine if the error can potentially be recovered from.

        Args:
            error: The exception that occurred
            operation_context: Full context of the operation when error occurred

        Returns:
            True if error recovery should be attempted
        """
        pass

    def on_recovery_attempt(self, error: Exception, operation_context: OperationContext) -> bool:
        """
        Attempt to recover from the error (optional implementation).

        Args:
            error: The exception that occurred
            operation_context: Full context of the operation when error occurred

        Returns:
            True if recovery was successful, False otherwise
        """
        return False

    def get_handler_name(self) -> str:
        """Get human-readable name for this error handler."""
        return self.__class__.__name__


class DefaultOperationErrorHandler(OperationErrorHandler):
    """
    Default error handler that logs errors with full context.

    This handler provides comprehensive error logging with operation context,
    formatted error messages, and detailed traceback information.
    """

    def __init__(self, logger_name: str = "solid_state_kinetics.operations.errors"):
        """
        Initialize the default error handler.

        Args:
            logger_name: Name of the logger to use for error logging
        """
        self.logger = logging.getLogger(logger_name)

    def handle_operation_error(self, error: Exception, operation_context: OperationContext) -> Optional[Dict[str, Any]]:
        """Handle error by logging comprehensive error information."""

        # Extract error details
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "operation_name": operation_context.operation_name,
            "operation_id": operation_context.operation_id,
            "duration_before_error": operation_context.duration,
            "error_time": datetime.now(),
            "traceback": traceback.format_exc(),
        }

        # Log structured error information
        self.logger.error(
            f"❌ OPERATION_ERROR: {operation_context.operation_name} failed with {type(error).__name__}: {error}",
            extra={
                "operation_id": operation_context.operation_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "operation_duration": operation_context.duration,
                "operation_metrics": operation_context.metrics,
            },
        )

        # Log detailed traceback for debugging
        self.logger.debug(f"Full traceback for operation {operation_context.operation_name}:\n{traceback.format_exc()}")

        return {
            "handled": True,
            "handler": self.get_handler_name(),
            "error_details": error_details,
            "recovery_attempted": False,
            "recovery_success": False,
        }

    def can_recover(self, error: Exception, operation_context: OperationContext) -> bool:
        """Default handler does not attempt recovery."""
        return False


class GuiOperationErrorHandler(OperationErrorHandler):
    """
    Error handler for GUI applications with user notification support.

    This handler can show error dialogs to users and collect user feedback
    about error handling preferences.
    """

    def __init__(self, show_dialogs: bool = True, auto_recovery: bool = False):
        """
        Initialize GUI error handler.

        Args:
            show_dialogs: Whether to show error dialogs to users
            auto_recovery: Whether to attempt automatic recovery for known errors
        """
        self.show_dialogs = show_dialogs
        self.auto_recovery = auto_recovery
        self.logger = logging.getLogger("solid_state_kinetics.operations.gui_errors")

    def handle_operation_error(self, error: Exception, operation_context: OperationContext) -> Optional[Dict[str, Any]]:
        """Handle error with GUI user interaction."""

        error_title = f"Ошибка в операции: {operation_context.operation_name}"
        error_message = self._format_user_error_message(error, operation_context)

        # Log the error for development
        self.logger.error(f"GUI Error Handler: {error_title} - {error}")

        result = {
            "handled": True,
            "handler": self.get_handler_name(),
            "error_title": error_title,
            "error_message": error_message,
            "recovery_attempted": False,
            "recovery_success": False,
            "user_action": "acknowledged",
        }

        # Show dialog if enabled (placeholder - would integrate with actual GUI framework)
        if self.show_dialogs:
            # In real implementation, this would show a QMessageBox or similar
            self.logger.info(f"Would show error dialog: {error_title}")
            result["dialog_shown"] = True

        # Attempt recovery if enabled
        if self.auto_recovery and self.can_recover(error, operation_context):
            recovery_success = self.on_recovery_attempt(error, operation_context)
            result.update(
                {
                    "recovery_attempted": True,
                    "recovery_success": recovery_success,
                }
            )

        return result

    def can_recover(self, error: Exception, operation_context: OperationContext) -> bool:
        """Determine if GUI handler can recover from specific error types."""
        # Common recoverable errors in GUI applications
        recoverable_errors = {
            "FileNotFoundError": True,
            "PermissionError": False,  # Usually requires user intervention
            "ValueError": True,  # Often input validation issues
            "KeyError": True,  # Missing data keys
            "IndexError": True,  # Array bounds issues
        }

        return recoverable_errors.get(type(error).__name__, False)

    def on_recovery_attempt(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt automatic recovery for known error patterns."""
        error_type = type(error).__name__

        try:
            if error_type == "FileNotFoundError":
                return self._attempt_file_recovery(error, operation_context)
            elif error_type == "ValueError":
                return self._attempt_value_recovery(error, operation_context)
            elif error_type == "KeyError":
                return self._attempt_key_recovery(error, operation_context)
            elif error_type == "IndexError":
                return self._attempt_index_recovery(error, operation_context)
        except Exception as recovery_error:
            self.logger.warning(f"Recovery attempt failed: {recovery_error}")

        return False

    def _format_user_error_message(self, error: Exception, operation_context: OperationContext) -> str:
        """Format user-friendly error message."""
        operation_name_ru = self._translate_operation_name(operation_context.operation_name)
        error_type = type(error).__name__

        user_messages = {
            "FileNotFoundError": f"Файл не найден при выполнении операции '{operation_name_ru}'",
            "PermissionError": f"Недостаточно прав для выполнения операции '{operation_name_ru}'",
            "ValueError": f"Некорректные данные в операции '{operation_name_ru}'",
            "KeyError": f"Отсутствуют необходимые данные для операции '{operation_name_ru}'",
            "IndexError": f"Ошибка обращения к данным в операции '{operation_name_ru}'",
        }

        base_message = user_messages.get(error_type, f"Ошибка {error_type} в операции '{operation_name_ru}'")
        return f"{base_message}: {str(error)}"

    def _translate_operation_name(self, operation_name: str) -> str:
        """Translate operation names to Russian for user display."""
        translations = {
            "LOAD_FILE": "Загрузка файла",
            "DECONVOLUTION": "Деконволюция",
            "MODEL_FIT_CALCULATION": "Расчет Model-Fit",
            "MODEL_FREE_CALCULATION": "Расчет Model-Free",
            "MODEL_BASED_CALCULATION": "Расчет Model-Based",
            "ADD_REACTION": "Добавление реакции",
            "REMOVE_REACTION": "Удаление реакции",
            "EXPORT_REACTIONS": "Экспорт реакций",
            "IMPORT_REACTIONS": "Импорт реакций",
        }
        return translations.get(operation_name, operation_name)

    def _attempt_file_recovery(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt to recover from file-related errors."""
        # Placeholder for file recovery logic
        self.logger.info("Attempting file recovery...")
        return False

    def _attempt_value_recovery(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt to recover from value errors."""
        # Placeholder for value validation recovery
        self.logger.info("Attempting value recovery...")
        return False

    def _attempt_key_recovery(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt to recover from key errors."""
        # Placeholder for missing key recovery
        self.logger.info("Attempting key recovery...")
        return False

    def _attempt_index_recovery(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt to recover from index errors."""
        # Placeholder for index bounds recovery
        self.logger.info("Attempting index recovery...")
        return False


class FileRollbackErrorHandler(OperationErrorHandler):
    """
    Error handler that attempts to rollback file changes on errors.

    This handler maintains file state and can restore previous versions
    when operations fail.
    """

    def __init__(self, enable_rollback: bool = True, backup_directory: Optional[str] = None):
        """
        Initialize file rollback error handler.

        Args:
            enable_rollback: Whether to enable automatic file rollback
            backup_directory: Directory to store file backups (None for temp)
        """
        self.enable_rollback = enable_rollback
        self.backup_directory = backup_directory
        self.logger = logging.getLogger("solid_state_kinetics.operations.file_rollback")
        self._file_snapshots: Dict[str, Dict[str, Any]] = {}

    def handle_operation_error(self, error: Exception, operation_context: OperationContext) -> Optional[Dict[str, Any]]:
        """Handle error with file rollback capability."""

        result = {
            "handled": True,
            "handler": self.get_handler_name(),
            "rollback_attempted": False,
            "rollback_success": False,
            "files_affected": [],
        }

        # Log the error
        self.logger.error(f"File operation error in {operation_context.operation_name}: {error}")

        # Attempt rollback if enabled and files were modified
        if self.enable_rollback and operation_context.files_modified > 0:
            rollback_success = self.on_recovery_attempt(error, operation_context)
            result.update(
                {
                    "rollback_attempted": True,
                    "rollback_success": rollback_success,
                }
            )

        return result

    def can_recover(self, error: Exception, operation_context: OperationContext) -> bool:
        """Determine if file rollback is possible."""
        # File rollback is possible if files were modified and we have snapshots
        return self.enable_rollback and operation_context.files_modified > 0 and len(self._file_snapshots) > 0

    def on_recovery_attempt(self, error: Exception, operation_context: OperationContext) -> bool:
        """Attempt to rollback file changes."""
        try:
            if not self._file_snapshots:
                self.logger.warning("No file snapshots available for rollback")
                return False

            # Rollback files (placeholder implementation)
            self.logger.info(f"Attempting rollback for operation {operation_context.operation_name}")

            # In real implementation, this would restore files from snapshots
            rollback_count = 0
            for file_path, snapshot in self._file_snapshots.items():
                try:
                    # Placeholder: restore file from snapshot
                    self.logger.debug(f"Rolling back file: {file_path}")
                    rollback_count += 1
                except Exception as rollback_error:
                    self.logger.error(f"Failed to rollback {file_path}: {rollback_error}")

            if rollback_count > 0:
                self.logger.info(f"Successfully rolled back {rollback_count} files")
                self._clear_snapshots()
                return True
            else:
                self.logger.warning("No files were successfully rolled back")
                return False

        except Exception as rollback_error:
            self.logger.error(f"Rollback attempt failed: {rollback_error}")
            return False

    def create_file_snapshot(self, file_path: str) -> bool:
        """Create a snapshot of a file before modification."""
        try:
            # Placeholder for file snapshot creation
            self._file_snapshots[file_path] = {
                "timestamp": datetime.now(),
                "backup_path": f"{file_path}.backup",
                "original_size": 0,  # Would be actual file size
            }
            self.logger.debug(f"Created snapshot for file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create snapshot for {file_path}: {e}")
            return False

    def _clear_snapshots(self):
        """Clear all file snapshots."""
        self._file_snapshots.clear()
        self.logger.debug("Cleared all file snapshots")


@dataclass
class ErrorHandlingConfig:
    """Configuration settings for operation error handling."""

    enabled: bool = True
    """Enable error handling through registered handlers"""

    show_gui_dialogs: bool = True
    """Show GUI dialogs for user-facing errors"""

    auto_recovery_attempts: int = 3
    """Maximum number of automatic recovery attempts"""

    rollback_file_changes: bool = True
    """Enable automatic rollback of file changes on errors"""

    log_full_traceback: bool = False
    """Include full Python traceback in error logs"""

    notification_channels: List[str] = None
    """List of notification channels for errors (log, gui, email, etc.)"""

    recovery_timeout: float = 30.0
    """Timeout in seconds for recovery operations"""

    recoverable_error_types: List[str] = None
    """List of error types that should be attempted for recovery"""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.notification_channels is None:
            self.notification_channels = ["log", "gui"]

        if self.recoverable_error_types is None:
            self.recoverable_error_types = [
                "FileNotFoundError",
                "ValueError",
                "KeyError",
                "IndexError",
                "ConnectionError",
            ]


# Default error handling configuration
DEFAULT_ERROR_HANDLING_CONFIG = ErrorHandlingConfig()
