# Log aggregator module for real-time log processing
# Provides structured aggregation and analysis of application logs

__version__ = "1.0.0"
__author__ = "Solid State Kinetics Team"

from .config import AggregationConfig, TabularFormattingConfig
from .error_expansion import ErrorContext, ErrorExpansionConfig, ErrorExpansionEngine
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
]
