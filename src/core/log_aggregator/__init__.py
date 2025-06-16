"""
MVP module for logging operations and sub-operations.

This module provides decorators and utilities for capturing and aggregating
operation execution logs in a structured, tabular format.

Architecture follows the project's principles:
- Loose coupling: Module operates through standard interfaces
- Asynchronous communication: Preserves Qt signals/slots pattern
- Centralized routing: Uses existing BaseSignals infrastructure
- Extensibility: Ready for future enhancements

Meta-operation clustering capabilities:
- Time-window clustering: Groups operations by execution proximity
- Name similarity clustering: Groups operations with similar names
- Target similarity clustering: Groups operations targeting same components
- Configurable detection strategies with minimal integration overhead
"""

from .aggregated_operation_logger import AggregatedOperationLogger, get_aggregated_logger, log_operation
from .detection_strategies import (
    NameSimilarityStrategy,
    SequenceCountStrategy,
    TargetClusterStrategy,
    TimeWindowStrategy,
)
from .error_handler import ErrorAnalysis, ErrorCategory, ErrorSeverity, SubOperationErrorHandler
from .meta_operation import MetaOperation
from .meta_operation_config import MetaOperationConfig, create_detector_from_config, get_default_detector
from .meta_operation_detector import MetaOperationDetector, MetaOperationStrategy
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
    "MetaOperation",
    "MetaOperationConfig",
    "create_detector_from_config",
    "get_default_detector",
    "MetaOperationDetector",
    "MetaOperationStrategy",
    "NameSimilarityStrategy",
    "TargetClusterStrategy",
    "TimeWindowStrategy",
    "SequenceCountStrategy",
]
