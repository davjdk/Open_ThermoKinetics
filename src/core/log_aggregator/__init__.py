"""
MVP module for logging operations and sub-operations.

This module provides decorators and utilities for capturing and aggregating
operation execution logs in a structured, tabular format.

Architecture follows the project's principles:
- Loose coupling: Module operates through standard interfaces
- Asynchronous communication: Preserves Qt signals/slots pattern
- Centralized routing: Uses existing BaseSignals infrastructure
- Extensibility: Ready for future enhancements
"""

from .aggregated_operation_logger import AggregatedOperationLogger, get_aggregated_logger, log_operation
from .error_handler import ErrorAnalysis, ErrorCategory, ErrorSeverity, SubOperationErrorHandler
from .operation_log import OperationLog
from .operation_logger import OperationLogger, operation
from .sub_operation_log import SubOperationLog
from .table_formatter import OperationTableFormatter, format_operation_log

__all__ = [
    "operation",
    "OperationLog",
    "OperationLogger",
    "SubOperationLog",
    "OperationTableFormatter",
    "format_operation_log",
    "AggregatedOperationLogger",
    "get_aggregated_logger",
    "log_operation",
    "ErrorAnalysis",
    "ErrorCategory",
    "ErrorSeverity",
    "SubOperationErrorHandler",
]
