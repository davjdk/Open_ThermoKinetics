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

    def __init__(self, include_error_details: bool = True):
        """
        Initialize the aggregated operation logger (only once).

        Args:
            include_error_details: Whether to include detailed error information
        """
        if self._initialized:
            return

        self._main_logger = LoggerManager().get_logger("solid_state_kinetics")

        # Load formatting configuration from logger_config
        self._load_formatting_config()

        self._formatter = OperationTableFormatter(
            include_error_details=include_error_details,
            table_format=self._table_format,
            minimalist_mode=self._minimalist_mode,
        )
        self._initialized = True

        # Initialize meta-operation detection
        from .meta_operation_config import get_default_detector

        self._meta_detector = get_default_detector()  # Initialize the aggregated logger
        self._setup_aggregated_logger()

    def _load_formatting_config(self) -> None:
        """Load formatting configuration from META_OPERATION_CONFIG."""
        try:
            from ..logger_config import META_OPERATION_CONFIG

            formatting_config = META_OPERATION_CONFIG.get("formatting", {})
            minimalist_config = META_OPERATION_CONFIG.get("minimalist_settings", {})

            # Determine if minimalist mode is enabled
            self._minimalist_mode = formatting_config.get("mode") == "minimalist"

            # Apply settings based on mode
            if self._minimalist_mode:
                # Override with minimalist settings
                self._table_format = minimalist_config.get("table_format", "simple")
                self._show_decorative_borders = minimalist_config.get("show_decorative_borders", False)
                self._show_completion_footer = minimalist_config.get("show_completion_footer", False)
                self._header_format = minimalist_config.get("header_format", "source_based")
            else:
                # Use standard settings
                self._table_format = formatting_config.get("table_format", "grid")
                self._show_decorative_borders = formatting_config.get("show_decorative_borders", True)
                self._show_completion_footer = formatting_config.get("show_completion_footer", True)
                self._header_format = formatting_config.get("header_format", "standard")

            self._include_source_info = formatting_config.get("include_source_info", True)
            self._table_separator = formatting_config.get("table_separator", "\n\n")

            self._main_logger.debug(
                f"Loaded formatting config: minimalist={self._minimalist_mode}, " f"table_format={self._table_format}"
            )

        except Exception as e:
            # Fallback to default values
            self._minimalist_mode = False
            self._table_format = "grid"
            self._show_decorative_borders = True
            self._show_completion_footer = True
            self._header_format = "standard"
            self._include_source_info = True
            self._table_separator = "\n\n"

            self._main_logger.warning(f"Failed to load formatting config, using defaults: {e}")

    def _setup_aggregated_logger(self) -> None:
        """Set up the aggregated operations logger with separate file handler."""
        try:
            # Get or create the aggregated operations logger
            logger_name = "aggregated_operations"
            self._aggregated_logger = logging.getLogger(logger_name)
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
            # Apply meta-operation detection if detector is available
            if self._meta_detector is not None:
                try:
                    self._meta_detector.detect_meta_operations(operation_log)
                except Exception as e:
                    # Meta-operation detection errors should not break logging
                    self._main_logger.debug(f"Meta-operation detection failed: {e}")

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

    def set_error_details_enabled(self, enabled: bool) -> None:
        """
        Enable or disable detailed error logging.

        Args:
            enabled: Whether to include detailed error information
        """
        if self._formatter:
            self._formatter.include_error_details = enabled

    def get_error_details_enabled(self) -> bool:
        """
        Check if detailed error logging is enabled.

        Returns:
            bool: True if detailed error logging is enabled
        """
        return self._formatter.include_error_details if self._formatter else True


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
