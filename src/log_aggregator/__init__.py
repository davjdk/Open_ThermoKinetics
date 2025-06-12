# Log aggregator module for real-time log processing
# Provides structured aggregation and analysis of application logs

__version__ = "1.0.0"
__author__ = "Solid State Kinetics Team"

from .config import AggregationConfig, TabularFormattingConfig
from .tabular_formatter import TableData, TabularFormatter

# Note: AggregatingHandler import disabled temporarily during Stage 1 development
# from .realtime_handler import AggregatingHandler

__all__ = [
    "AggregationConfig",
    "TabularFormattingConfig",
    "TabularFormatter",
    "TableData",
    # "AggregatingHandler",
]
