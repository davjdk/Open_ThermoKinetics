"""
Aggregated operation logger for writing formatted operation logs to separate file.

This module implements the AggregatedOperationLogger class that integrates with the existing
LoggerManager to provide separate aggregated operation logging functionality.

Key components:
- AggregatedOperationLogger: Singleton class for aggregated operation logging
- Integration with LoggerManager for consistent logging configuration
- Separate log file with rotation for aggregated operations
- Error handling that doesn't disrupt main application flow
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from ..logger_config import LoggerManager
from .operation_log import OperationLog
from .table_formatter import OperationTableFormatter


class AggregatedOperationLogger:
    """
    Singleton logger for aggregated operation logs.

    This class manages the separate logging of formatted operation tables
    to the aggregated_operations.log file with proper rotation and error handling.
    """

    _instance: Optional["AggregatedOperationLogger"] = None
    _initialized: bool = False

    def __new__(cls) -> "AggregatedOperationLogger":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the aggregated operation logger (only once)."""
        if self._initialized:
            return

        self._logger_name = "solid_state_kinetics.operations"
        self._formatter = OperationTableFormatter()
        self._main_logger = LoggerManager.get_logger(__name__)

        # Initialize the aggregated logger
        self._setup_aggregated_logger()
        self._initialized = True

    def _setup_aggregated_logger(self) -> None:
        """Set up the aggregated operations logger with separate file handler."""
        try:
            # Get or create the aggregated operations logger
            self._aggregated_logger = logging.getLogger(self._logger_name)
            self._aggregated_logger.setLevel(logging.INFO)

            # Clear any existing handlers to avoid duplicates
            self._aggregated_logger.handlers.clear()

            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            # Set up rotating file handler for aggregated operations
            log_file = logs_dir / "aggregated_operations.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)

            # Create a simple formatter for aggregated logs (no timestamps needed)
            # Since our formatted tables already include timestamps
            formatter = logging.Formatter("%(message)s")
            file_handler.setFormatter(formatter)

            # Add handler to aggregated logger
            self._aggregated_logger.addHandler(file_handler)

            # Prevent propagation to root logger to avoid duplicate logs
            self._aggregated_logger.propagate = False

            self._main_logger.info(f"Aggregated operations logger configured: {log_file}")

        except Exception as e:
            self._main_logger.error(f"Failed to setup aggregated operations logger: {e}")
            # Set aggregated logger to None to indicate failure
            self._aggregated_logger = None

    def log_operation(self, operation_log: OperationLog) -> None:
        """
        Log a formatted operation to the aggregated operations file.

        Args:
            operation_log: The OperationLog instance to format and log
        """
        if operation_log is None:
            self._main_logger.warning("Attempted to log None operation")
            return

        try:
            # Format the operation log using the table formatter
            formatted_log = self._formatter.format_operation_log(operation_log)

            # Log to aggregated operations file if logger is available
            if self._aggregated_logger is not None:
                # Add separator line before operation for readability
                separator = "=" * 80
                self._aggregated_logger.info(separator)
                self._aggregated_logger.info(formatted_log)
                self._aggregated_logger.info(separator)
            else:
                # Fallback to main logger if aggregated logger failed to initialize
                self._main_logger.warning("Aggregated logger not available, using main logger")
                self._main_logger.info(f"AGGREGATED OPERATION LOG:\n{formatted_log}")

        except Exception as e:
            # Error in logging should not disrupt main application flow
            self._main_logger.error(f"Failed to log aggregated operation: {e}")
            self._main_logger.debug(f"Operation details: {operation_log.operation_name}")

    def format_operation_log(self, operation_log: OperationLog) -> str:
        """
        Format an operation log without writing to file.

        Args:
            operation_log: The OperationLog instance to format

        Returns:
            str: Formatted operation log string
        """
        try:
            return self._formatter.format_operation_log(operation_log)
        except Exception as e:
            self._main_logger.error(f"Failed to format operation log: {e}")
            return f"Error formatting operation: {operation_log.operation_name if operation_log else 'Unknown'}"

    def get_log_file_path(self) -> Optional[Path]:
        """
        Get the path to the aggregated operations log file.

        Returns:
            Path to the log file or None if not initialized
        """
        if self._aggregated_logger and self._aggregated_logger.handlers:
            handler = self._aggregated_logger.handlers[0]
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                return Path(handler.baseFilename)
        return None

    def is_configured(self) -> bool:
        """
        Check if the aggregated logger is properly configured.

        Returns:
            bool: True if logger is configured and ready to use
        """
        return self._aggregated_logger is not None and self._initialized


# Convenience function for getting the singleton instance
def get_aggregated_logger() -> AggregatedOperationLogger:
    """Get the singleton instance of AggregatedOperationLogger."""
    return AggregatedOperationLogger()


# For backward compatibility and convenience
def log_operation(operation_log: OperationLog) -> None:
    """
    Convenience function to log an operation using the singleton logger.

    Args:
        operation_log: The OperationLog instance to log
    """
    get_aggregated_logger().log_operation(operation_log)
