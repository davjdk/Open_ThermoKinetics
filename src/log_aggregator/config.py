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

    context_lines: int = 3
    """Number of preceding context lines to include in error expansion"""

    save_context: bool = False
    """Whether to save error context to disk"""

    trace_depth: int = 10
    """Maximum depth of operation trace to analyze for errors"""

    error_threshold_level: str = "ERROR"
    """Minimum log level to trigger error expansion (WARNING/ERROR/CRITICAL)"""

    context_time_window: float = 5.0
    """Time window in seconds to look for related operations in error context"""

    # New adaptive behavior settings
    adaptive_threshold: bool = True
    """Whether to adaptively adjust thresholds based on load"""

    disable_on_high_load: bool = True
    """Whether to disable error expansion during high load"""

    max_expansions_per_minute: int = 10
    """Maximum number of error expansions per minute"""


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

    # New priority-based configuration
    priority_tables: List[str] = field(
        default_factory=lambda: ["operation_cascade", "request_response_cycle", "error_analysis"]
    )
    """High-priority tables that should always be formatted"""

    low_priority_tables: List[str] = field(
        default_factory=lambda: ["plot_lines_addition", "gui_updates", "file_operations"]
    )
    """Low-priority tables that can be disabled under load"""

    disable_low_priority_on_load: bool = True
    """Whether to disable low-priority tables during high load"""

    enabled_tables: Optional[List[str]] = None
    """Specific list of enabled table types (overrides auto_format_patterns)"""

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
    """Output format: 'simple', 'enhanced', 'tabular'"""  # Debug and monitoring
    enable_stats_logging: bool = True
    """Whether to enable statistics logging"""

    stats_interval_seconds: int = 60
    """Interval for statistics reporting"""

    debug_mode: bool = False
    """Whether debug mode is enabled"""

    # Recursion prevention (Stage 2)
    prevent_internal_recursion: bool = True
    """Whether to prevent processing of internal aggregator logs"""

    max_internal_errors: int = 10
    """Maximum number of internal errors before degradation"""

    error_reset_interval: int = 300
    """Time interval in seconds to reset internal error counter"""

    separate_debug_logging: bool = True
    """Whether to use separate debug logging for internal aggregator logs"""

    # Stage 3: Optimization Monitoring settings
    optimization_monitoring_enabled: bool = True
    """Whether optimization monitoring is enabled"""

    optimization_update_interval: float = 1.0
    """Interval in seconds between optimization monitoring updates"""

    optimization_progress_report_interval: float = 10.0
    """Interval for optimization progress reporting in seconds"""

    optimization_convergence_window: int = 10
    """Number of iterations to check for convergence"""

    optimization_stall_threshold: int = 50
    """Number of iterations without improvement to consider stalled"""

    # Performance monitoring settings
    performance_monitoring_enabled: bool = True
    """Whether performance monitoring is enabled"""

    performance_collection_interval: float = 5.0
    """Interval in seconds between performance metric collection"""

    performance_memory_threshold_mb: float = 500.0
    """Memory threshold in MB for performance warnings"""

    performance_processing_time_threshold_ms: float = 100.0
    """Processing time threshold in ms for performance warnings"""

    # Operation monitoring settings
    operation_monitoring_enabled: bool = True
    """Whether operation monitoring is enabled"""

    operation_timeout_seconds: float = 300.0
    """Timeout for individual operations"""

    operation_flow_timeout_seconds: float = 600.0
    """Timeout for operation flows"""

    operation_slow_threshold_ms: float = 1000.0
    """Threshold for slow operation warnings"""

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
        return cls()

    @classmethod
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


@dataclass
class OptimizationMonitoringConfig:
    """Configuration for optimization monitoring."""

    enabled: bool = True
    """Whether optimization monitoring is enabled"""

    update_interval: float = 1.0
    """Interval in seconds between monitoring updates"""

    progress_report_interval: float = 10.0
    """Interval for progress reporting in seconds"""

    convergence_window: int = 10
    """Number of iterations to check for convergence"""

    stall_threshold: int = 50
    """Number of iterations without improvement to consider stalled"""

    min_improvement_threshold: float = 1e-6
    """Minimum improvement to consider progress"""

    max_error_history: int = 1000
    """Maximum number of error values to keep in history"""

    enable_convergence_analysis: bool = True
    """Whether to perform convergence analysis"""

    enable_time_estimation: bool = True
    """Whether to estimate remaining time"""

    enable_parameter_tracking: bool = True
    """Whether to track parameter changes"""

    log_level: str = "INFO"
    """Log level for optimization monitoring"""


@dataclass
class PerformanceMonitoringConfig:
    """Configuration for performance monitoring."""

    enabled: bool = True
    """Whether performance monitoring is enabled"""

    collection_interval: float = 5.0
    """Interval in seconds between metric collection"""

    history_size: int = 1000
    """Number of metrics to keep in history"""

    memory_threshold_mb: float = 500.0
    """Memory threshold in MB for warnings"""

    processing_time_threshold_ms: float = 100.0
    """Processing time threshold in ms for warnings"""

    enable_detailed_profiling: bool = False
    """Whether to enable detailed profiling (impacts performance)"""

    enable_gc_monitoring: bool = True
    """Whether to monitor garbage collection"""

    log_warnings: bool = True
    """Whether to log performance warnings"""

    log_level: str = "INFO"
    """Log level for performance monitoring"""


@dataclass
class OperationMonitoringConfig:
    """Configuration for operation monitoring."""

    enabled: bool = True
    """Whether operation monitoring is enabled"""

    max_operation_history: int = 10000
    """Maximum number of operations to keep in history"""

    max_flow_history: int = 1000
    """Maximum number of flows to keep in history"""

    operation_timeout_seconds: float = 300.0
    """Timeout for individual operations"""

    flow_timeout_seconds: float = 600.0
    """Timeout for operation flows"""

    enable_performance_tracking: bool = True
    """Whether to track operation performance"""

    enable_flow_analysis: bool = True
    """Whether to analyze operation flows"""

    enable_memory_tracking: bool = True
    """Whether to track memory usage"""

    slow_operation_threshold_ms: float = 1000.0
    """Threshold for slow operation warnings"""

    flow_analysis_window_seconds: float = 60.0
    """Time window for flow analysis"""

    log_level: str = "INFO"
    """Log level for operation monitoring"""
