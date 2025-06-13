"""
Configuration module for log aggregation system.

This module provides basic configuration settings for the log aggregation
system, including buffer management and pattern detection parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ErrorExpansionConfig:
    """Configuration for error expansion functionality."""

    enabled: bool = True
    """Whether error expansion is enabled"""

    immediate_expansion: bool = True
    """Whether to expand errors immediately when detected"""

    context_lines: int = 5
    """Number of preceding context lines to include in error expansion"""

    save_context: bool = False
    """Whether to save error context to disk"""

    trace_depth: int = 10
    """Maximum depth of operation trace to analyze for errors"""

    error_threshold_level: str = "WARNING"
    """Minimum log level to trigger error expansion (WARNING/ERROR/CRITICAL)"""

    context_time_window: float = 10.0
    """Time window in seconds to look for related operations in error context"""


@dataclass
class TabularFormattingConfig:
    """Configuration for tabular formatting of aggregated patterns."""

    enabled: bool = True
    """Whether tabular formatting is enabled"""

    max_table_width: int = 120
    """Maximum width of generated tables in characters"""

    max_rows_per_table: int = 20
    """Maximum number of rows per table"""

    ascii_tables: bool = True
    """Whether to use ASCII table formatting"""

    include_summaries: bool = True
    """Whether to include summary information below tables"""

    auto_format_patterns: Optional[List[str]] = None
    """List of pattern types to automatically format as tables"""

    def __post_init__(self):
        """Initialize default values for complex fields."""
        if self.auto_format_patterns is None:
            self.auto_format_patterns = [
                "plot_lines_addition",
                "cascade_component_initialization",
                "request_response_cycle",
                "file_operations",
                "gui_updates",
            ]


@dataclass
class OperationAggregationConfig:
    """Configuration for operation aggregation."""

    enabled: bool = True
    """Whether operation aggregation is enabled"""

    cascade_window: float = 1.0
    """Time window in seconds to group operations into cascades"""

    min_cascade_size: int = 3
    """Minimum number of operations to consider a cascade"""

    root_operations: Set[str] = field(
        default_factory=lambda: {
            "ADD_REACTION",
            "REMOVE_REACTION",
            "MODEL_BASED_CALCULATION",
            "DECONVOLUTION",
            "MODEL_FIT_CALCULATION",
            "MODEL_FREE_CALCULATION",
            "LOAD_FILE",
            "TO_DTG",
            "SMOOTH_DATA",
            "SUBTRACT_BACKGROUND",
            "GET_DF_DATA",
            "UPDATE_VALUE",
            "SET_VALUE",
        }
    )
    """Set of operations that can start a cascade"""


@dataclass
class ValueAggregationConfig:
    """Configuration for value aggregation."""

    enabled: bool = True
    """Whether value aggregation is enabled"""

    array_threshold: int = 10
    """Minimum array size to trigger compression"""

    dataframe_threshold: int = 5
    """Minimum dataframe size to trigger compression"""

    dict_threshold: int = 8
    """Minimum dict size to trigger compression"""

    string_threshold: int = 200
    """Minimum string length to trigger compression"""

    cache_size_limit: int = 100
    """Maximum number of compressed values to cache"""


@dataclass
class AggregationConfig:
    """
    Full configuration for log aggregation system with all components.

    Includes all features from stages 1-5: basic aggregation, enhanced patterns,
    tabular formatting, error expansion, operation aggregation, and value aggregation.
    """

    # Buffer management
    buffer_size: int = 1000
    """Maximum number of log records to keep in buffer before processing"""

    flush_interval: float = 2.0
    """Time interval in seconds to process buffer even if not full"""

    context_buffer_size: int = 20
    """Number of context records to keep for error expansion"""

    # Pattern detection
    min_pattern_entries: int = 3
    """Minimum number of entries to consider a pattern for aggregation"""

    time_window_seconds: int = 5
    """Time window for pattern grouping"""

    pattern_priority_threshold: str = "medium"
    """Priority threshold for pattern detection"""  # Component configurations
    error_expansion: ErrorExpansionConfig = None
    """Configuration for error expansion component"""

    tabular_formatting: TabularFormattingConfig = None
    """Configuration for tabular formatting component"""

    operation_aggregation: OperationAggregationConfig = None
    """Configuration for operation aggregation component"""

    value_aggregation: ValueAggregationConfig = None
    """Configuration for value aggregation component"""

    # Performance settings
    max_processing_time_ms: float = 100.0
    """Maximum time in milliseconds allowed for processing"""

    enable_async_processing: bool = False
    """Whether to enable asynchronous processing"""

    # Output settings
    compression_threshold: float = 0.3
    """Threshold for compression ratio reporting"""

    output_format: str = "enhanced"
    """Output format: 'simple', 'enhanced', 'tabular'"""

    # Debug and monitoring
    enable_stats_logging: bool = True
    """Whether to enable statistics logging"""

    stats_interval_seconds: int = 60
    """Interval for statistics reporting"""

    debug_mode: bool = False
    """Whether debug mode is enabled"""

    # Legacy settings for backward compatibility
    pattern_similarity_threshold: float = 0.8
    enhanced_patterns_enabled: bool = True
    pattern_type_priorities: Dict[str, int] = None
    pattern_time_windows: Dict[str, float] = None
    min_cascade_depth: int = 3
    max_pattern_metadata_size: int = 1000
    error_expansion_enabled: bool = True
    error_context_lines: int = 5
    error_trace_depth: int = 10
    error_immediate_expansion: bool = True
    error_threshold_level: str = "WARNING"
    error_context_time_window: float = 10.0
    max_processing_time: float = 0.1
    enabled: bool = True
    collect_statistics: bool = True
    operation_aggregation_enabled: bool = True
    operation_cascade_window: float = 1.0
    operation_min_cascade_size: int = 3
    value_aggregation_enabled: bool = True
    value_array_threshold: int = 10
    value_dataframe_threshold: int = 5
    value_dict_threshold: int = 8
    value_string_threshold: int = 200
    value_cache_size_limit: int = 100

    def __post_init__(self):
        """Initialize default values for complex fields."""
        if self.pattern_type_priorities is None:
            self.pattern_type_priorities = {
                "plot_lines_addition": 5,
                "cascade_component_initialization": 4,
                "request_response_cycle": 3,
                "file_operations": 2,
                "gui_updates": 1,
                "basic_similarity": 0,
            }

        if self.pattern_time_windows is None:
            self.pattern_time_windows = {
                "plot_lines_addition": 2.0,
                "cascade_component_initialization": 5.0,
                "request_response_cycle": 1.0,
                "file_operations": 10.0,
                "gui_updates": 0.5,
                "basic_similarity": 5.0,
            }

        if self.tabular_formatting is None:
            self.tabular_formatting = TabularFormattingConfig()

        if self.operation_aggregation is None:
            self.operation_aggregation = OperationAggregationConfig()

        if self.value_aggregation is None:
            self.value_aggregation = ValueAggregationConfig()

    @classmethod
    def default(cls) -> "AggregationConfig":
        """Create default configuration."""
        return cls() @ classmethod

    def minimal(cls) -> "AggregationConfig":
        """Create minimal configuration for development/testing."""
        return cls(buffer_size=20, flush_interval=2.0, min_pattern_entries=2, pattern_similarity_threshold=0.9)

    @classmethod
    def create_minimal(cls) -> "AggregationConfig":
        """Minimal configuration for basic usage."""
        return cls(
            buffer_size=500,
            flush_interval=1.0,
            min_pattern_entries=2,
            error_expansion=ErrorExpansionConfig(enabled=True, immediate_expansion=True),
            tabular_formatting=TabularFormattingConfig(enabled=True, max_rows_per_table=10),
            operation_aggregation=OperationAggregationConfig(enabled=True, cascade_window=1.0, min_cascade_size=3),
            value_aggregation=ValueAggregationConfig(enabled=True, array_threshold=5, dataframe_threshold=3),
        )

    @classmethod
    def create_performance(cls) -> "AggregationConfig":
        """Configuration for high performance."""
        return cls(
            buffer_size=2000,
            flush_interval=0.5,
            min_pattern_entries=5,
            max_processing_time_ms=50.0,
            enable_async_processing=True,
            error_expansion=ErrorExpansionConfig(enabled=True, immediate_expansion=False),
            tabular_formatting=TabularFormattingConfig(
                enabled=False  # Disabled for performance
            ),
            operation_aggregation=OperationAggregationConfig(
                enabled=True,
                cascade_window=0.5,  # More aggressive aggregation
                min_cascade_size=5,
            ),
            value_aggregation=ValueAggregationConfig(
                enabled=True,
                array_threshold=3,  # More aggressive compression
                dataframe_threshold=2,
                cache_size_limit=50,  # Less cache for performance
            ),
        )

    @classmethod
    def create_detailed(cls) -> "AggregationConfig":
        """Configuration for maximum detail."""
        return cls(
            buffer_size=1500,
            flush_interval=3.0,
            min_pattern_entries=2,
            context_buffer_size=50,
            error_expansion=ErrorExpansionConfig(enabled=True, context_lines=10, save_context=True),
            tabular_formatting=TabularFormattingConfig(enabled=True, include_summaries=True, max_rows_per_table=30),
            operation_aggregation=OperationAggregationConfig(
                enabled=True,
                cascade_window=2.0,  # More time for grouping
                min_cascade_size=2,  # Lower threshold for detail
            ),
            value_aggregation=ValueAggregationConfig(
                enabled=True,
                array_threshold=15,  # Less aggressive compression
                dataframe_threshold=8,
                cache_size_limit=200,  # More cache for context
            ),
            enable_stats_logging=True,
            debug_mode=True,
        )

    def validate(self) -> bool:
        """
        Validate configuration parameters.

        Returns:
            True if configuration is valid, False otherwise
        """
        if self.buffer_size <= 0:
            return False
        if self.flush_interval <= 0:
            return False
        if self.min_pattern_entries < 1:
            return False
        if not (0.0 <= self.pattern_similarity_threshold <= 1.0):
            return False
        if self.max_processing_time <= 0:
            return False
        if self.min_cascade_depth < 2:
            return False
        if self.max_pattern_metadata_size <= 0:
            return False

        return True

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for serialization."""
        return {
            "buffer_size": self.buffer_size,
            "flush_interval": self.flush_interval,
            "context_buffer_size": self.context_buffer_size,
            "min_pattern_entries": self.min_pattern_entries,
            "time_window_seconds": self.time_window_seconds,
            "pattern_priority_threshold": self.pattern_priority_threshold,
            "max_processing_time_ms": self.max_processing_time_ms,
            "enable_async_processing": self.enable_async_processing,
            "compression_threshold": self.compression_threshold,
            "output_format": self.output_format,
            "enable_stats_logging": self.enable_stats_logging,
            "stats_interval_seconds": self.stats_interval_seconds,
            "debug_mode": self.debug_mode,
            "error_expansion": {
                "enabled": self.error_expansion.enabled if self.error_expansion else True,
                "immediate_expansion": self.error_expansion.immediate_expansion if self.error_expansion else True,
                "context_lines": self.error_expansion.context_lines if self.error_expansion else 5,
                "save_context": self.error_expansion.save_context if self.error_expansion else False,
            }
            if self.error_expansion
            else None,
            "tabular_formatting": {
                "enabled": self.tabular_formatting.enabled if self.tabular_formatting else True,
                "max_rows_per_table": self.tabular_formatting.max_rows_per_table if self.tabular_formatting else 20,
                "include_summaries": self.tabular_formatting.include_summaries if self.tabular_formatting else True,
            }
            if self.tabular_formatting
            else None,
            "operation_aggregation": {
                "enabled": self.operation_aggregation.enabled if self.operation_aggregation else True,
                "cascade_window": self.operation_aggregation.cascade_window if self.operation_aggregation else 1.0,
                "min_cascade_size": self.operation_aggregation.min_cascade_size if self.operation_aggregation else 3,
            }
            if self.operation_aggregation
            else None,
            "value_aggregation": {
                "enabled": self.value_aggregation.enabled if self.value_aggregation else True,
                "array_threshold": self.value_aggregation.array_threshold if self.value_aggregation else 10,
                "dataframe_threshold": self.value_aggregation.dataframe_threshold if self.value_aggregation else 5,
                "cache_size_limit": self.value_aggregation.cache_size_limit if self.value_aggregation else 100,
            }
            if self.value_aggregation
            else None,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "AggregationConfig":
        """Create configuration from dictionary."""
        config = cls()

        # Update basic fields
        for key, value in config_dict.items():
            if hasattr(config, key) and not isinstance(value, dict):
                setattr(config, key, value)

        # Update component configurations
        if "error_expansion" in config_dict and config_dict["error_expansion"]:
            config.error_expansion = ErrorExpansionConfig(**config_dict["error_expansion"])

        if "tabular_formatting" in config_dict and config_dict["tabular_formatting"]:
            config.tabular_formatting = TabularFormattingConfig(**config_dict["tabular_formatting"])

        if "operation_aggregation" in config_dict and config_dict["operation_aggregation"]:
            config.operation_aggregation = OperationAggregationConfig(**config_dict["operation_aggregation"])

        if "value_aggregation" in config_dict and config_dict["value_aggregation"]:
            config.value_aggregation = ValueAggregationConfig(**config_dict["value_aggregation"])

        return config
