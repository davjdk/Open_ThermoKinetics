# Log aggregator module for real-time log processing
# Provides structured aggregation and analysis of application logs

__version__ = "1.0.0"
__author__ = "Solid State Kinetics Team"

from .config import AggregationConfig, TabularFormattingConfig
from .error_expansion import ErrorContext, ErrorExpansionConfig, ErrorExpansionEngine
from .operation_decorator import operation as enhanced_operation
from .operation_logger import OperationContext, OperationLogger, log_operation, operation, operation_logger
from .operation_metaclass import AutoOperationMeta, OperationAwareMixin, operation_aware_class
from .realtime_handler import AggregatingHandler
from .tabular_formatter import TableData, TabularFormatter

__all__ = [
    "AggregationConfig",
    "TabularFormattingConfig",
    "TabularFormatter",
    "TableData",
    "AggregatingHandler",
    "ErrorExpansionEngine",
    "ErrorExpansionConfig",
    "ErrorContext",
    "OperationContext",
    "OperationLogger",
    "log_operation",
    "operation",
    "operation_logger",
    "enhanced_operation",
    "AutoOperationMeta",
    "OperationAwareMixin",
    "operation_aware_class",
]
