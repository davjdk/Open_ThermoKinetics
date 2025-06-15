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

from .operation_logger import OperationLogger, operation
from .sub_operation_log import SubOperationLog

__all__ = ["operation", "OperationLogger", "SubOperationLog"]
