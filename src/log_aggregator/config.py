"""
Configuration module for log aggregation system.

This module provides basic configuration settings for the log aggregation
system, including buffer management and pattern detection parameters.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
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


DEFAULT_OPERATION_LOGGING_CONFIG = {
    "logging": {
        "operation_time_frame": 1.0,
        "cascade_window": 1.5,
        "operation_timeout": 300.0,
        "nested_operation_timeout": 60.0,
        "aggregate_nested_operations": True,
        "max_operation_depth": 10,
        "enable_operation_grouping": True,
        "group_by_thread": True,
        "tabulate_enabled": True,
        "tabulate_format": "grid",
        "force_ascii_tables": True,
        "table_max_width": 120,
        "table_headers": True,
        "use_unicode_symbols": False,
        "timestamp_format": "%Y-%m-%d %H:%M:%S",
        "duration_precision": 3,
        "max_error_message_length": 100,
        "detail_level": "normal",
        "include_user_metrics": True,
        "include_file_metrics": True,
        "include_performance_metrics": True,
        "exclude_operations": [],
        "include_only_operations": [],
        "min_operation_duration": 0.0,
        "log_full_traceback": False,
        "auto_recovery_enabled": True,
        "max_recovery_attempts": 3,
        "enable_async_logging": False,
        "buffer_size": 1000,
        "flush_interval": 5.0,
    },
    "tabular": {
        "enabled": True,
        "format_style": "grid",
        "headers_enabled": True,
        "max_table_width": 120,
        "max_rows_per_table": 20,
        "property_column_width": 20,
        "value_column_width": 40,
        "number_format": ".3f",
        "align_numbers": "right",
        "align_text": "left",
        "show_summary": True,
        "compact_mode": False,
        "ascii_only": True,
        "priority_tables": ["operation_summary", "error_analysis", "cascade_operations"],
        "success_symbol": "[OK]",
        "error_symbol": "[ERR]",
        "timeout_symbol": "[TMO]",
        "running_symbol": "[RUN]",
    },
    "metrics": {
        "collect_timing_metrics": True,
        "collect_memory_metrics": False,
        "collect_cpu_metrics": False,
        "collect_io_metrics": True,
        "track_file_operations": True,
        "track_file_sizes": True,
        "track_file_modifications": True,
        "track_reaction_metrics": True,
        "track_optimization_metrics": True,
        "track_convergence_metrics": True,
        "track_quality_metrics": True,
        "allow_custom_metrics": True,
        "max_custom_metrics": 50,
        "custom_metrics_prefix": "user_",
        "compress_large_data": True,
        "array_compression_threshold": 10,
        "dataframe_compression_threshold": 5,
        "string_compression_threshold": 200,
    },
}


def get_default_operation_config() -> Dict:
    """
    Get default operation logging configuration.

    Returns:
        Dictionary with default configuration settings
    """
    return DEFAULT_OPERATION_LOGGING_CONFIG.copy()


def update_config_from_env(config: Dict = None) -> Dict:
    """
    Update configuration with environment variables.

    Args:
        config: Configuration dictionary to update (uses default if None)

    Returns:
        Updated configuration dictionary
    """
    if config is None:
        config = get_default_operation_config()

    # Environment variable mappings
    env_mappings = {
        # Logging settings
        "SSK_OPERATION_TIME_FRAME": ("logging", "operation_time_frame", float),
        "SSK_CASCADE_WINDOW": ("logging", "cascade_window", float),
        "SSK_OPERATION_TIMEOUT": ("logging", "operation_timeout", float),
        "SSK_DETAIL_LEVEL": ("logging", "detail_level", str),
        "SSK_USE_UNICODE": ("logging", "use_unicode_symbols", bool),
        "SSK_ENABLE_ASYNC": ("logging", "enable_async_logging", bool),
        "SSK_BUFFER_SIZE": ("logging", "buffer_size", int),
        "SSK_FLUSH_INTERVAL": ("logging", "flush_interval", float),
        # Tabular settings
        "SSK_TABULATE_FORMAT": ("tabular", "format_style", str),
        "SSK_TABLE_MAX_WIDTH": ("tabular", "max_table_width", int),
        "SSK_ASCII_ONLY": ("tabular", "ascii_only", bool),
        "SSK_SHOW_HEADERS": ("tabular", "headers_enabled", bool),
        "SSK_MAX_ROWS": ("tabular", "max_rows_per_table", int),
        # Metrics settings
        "SSK_COLLECT_MEMORY": ("metrics", "collect_memory_metrics", bool),
        "SSK_COLLECT_CPU": ("metrics", "collect_cpu_metrics", bool),
        "SSK_TRACK_FILES": ("metrics", "track_file_operations", bool),
        "SSK_TRACK_OPTIMIZATION": ("metrics", "track_optimization_metrics", bool),
        "SSK_MAX_CUSTOM_METRICS": ("metrics", "max_custom_metrics", int),
    }

    for env_var, (section, key, value_type) in env_mappings.items():
        if env_var in os.environ:
            raw_value = os.environ[env_var]
            try:
                if value_type is bool:
                    value = raw_value.lower() in ("true", "1", "yes", "on")
                elif value_type is float:
                    value = float(raw_value)
                elif value_type is int:
                    value = int(raw_value)
                else:
                    value = raw_value

                if section in config:
                    config[section][key] = value

            except (ValueError, TypeError):
                # Ignore invalid environment variable values
                pass

    return config


def save_config_to_file(config: Dict, file_path: str) -> bool:
    """
    Save configuration to JSON file.

    Args:
        config: Configuration dictionary to save
        file_path: Path to save the configuration file

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_config_from_file(file_path: str) -> Optional[Dict]:
    """
    Load configuration from JSON file.

    Args:
        file_path: Path to the configuration file

    Returns:
        Configuration dictionary if loaded successfully, None otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def validate_operation_config(config: Dict) -> List[str]:
    """
    Validate operation configuration settings.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validate each section separately
    if "logging" in config:
        errors.extend(_validate_logging_config(config["logging"]))

    if "tabular" in config:
        errors.extend(_validate_tabular_config(config["tabular"]))

    if "metrics" in config:
        errors.extend(_validate_metrics_config(config["metrics"]))

    return errors


def _validate_logging_config(logging_config: Dict) -> List[str]:
    """Validate logging configuration section."""
    errors = []

    # Check required numeric fields
    numeric_fields = {
        "operation_time_frame": (0, float("inf")),
        "cascade_window": (0, float("inf")),
        "operation_timeout": (0, float("inf")),
        "nested_operation_timeout": (0, float("inf")),
        "max_operation_depth": (1, 1000),
        "duration_precision": (0, 10),
        "max_error_message_length": (10, 10000),
        "max_recovery_attempts": (0, 100),
        "buffer_size": (1, 100000),
        "flush_interval": (0.1, 3600.0),
    }

    for field_name, (min_val, max_val) in numeric_fields.items():
        value = logging_config.get(field_name)
        if value is not None:
            if not isinstance(value, (int, float)) or not (min_val <= value <= max_val):
                errors.append(f"logging.{field_name} must be between {min_val} and {max_val}")

    # Check enum fields
    valid_detail_levels = ["minimal", "normal", "detailed", "debug"]
    detail_level = logging_config.get("detail_level")
    if detail_level and detail_level not in valid_detail_levels:
        errors.append(f"logging.detail_level must be one of {valid_detail_levels}")

    valid_formats = ["grid", "simple", "plain", "pipe", "orgtbl", "rst", "mediawiki", "html", "latex"]
    tabulate_format = logging_config.get("tabulate_format")
    if tabulate_format and tabulate_format not in valid_formats:
        errors.append(f"logging.tabulate_format must be one of {valid_formats}")

    return errors


def _validate_tabular_config(tabular_config: Dict) -> List[str]:
    """Validate tabular configuration section."""
    errors = []

    # Check numeric constraints
    table_width = tabular_config.get("max_table_width")
    if table_width is not None and (not isinstance(table_width, int) or table_width < 50):
        errors.append("tabular.max_table_width must be at least 50")

    max_rows = tabular_config.get("max_rows_per_table")
    if max_rows is not None and (not isinstance(max_rows, int) or max_rows < 1):
        errors.append("tabular.max_rows_per_table must be at least 1")

    col_width = tabular_config.get("property_column_width")
    if col_width is not None and (not isinstance(col_width, int) or col_width < 5):
        errors.append("tabular.property_column_width must be at least 5")

    val_width = tabular_config.get("value_column_width")
    if val_width is not None and (not isinstance(val_width, int) or val_width < 5):
        errors.append("tabular.value_column_width must be at least 5")

    # Check format style
    valid_styles = ["grid", "simple", "plain", "pipe", "orgtbl", "rst", "mediawiki", "html", "latex"]
    format_style = tabular_config.get("format_style")
    if format_style and format_style not in valid_styles:
        errors.append(f"tabular.format_style must be one of {valid_styles}")

    return errors


def _validate_metrics_config(metrics_config: Dict) -> List[str]:
    """Validate metrics configuration section."""
    errors = []

    max_custom = metrics_config.get("max_custom_metrics")
    if max_custom is not None and (not isinstance(max_custom, int) or max_custom < 0):
        errors.append("metrics.max_custom_metrics must be non-negative")

    # Check compression thresholds
    thresholds = [
        ("array_compression_threshold", 1, 1000),
        ("dataframe_compression_threshold", 1, 1000),
        ("string_compression_threshold", 10, 10000),
    ]

    for field_name, min_val, max_val in thresholds:
        value = metrics_config.get(field_name)
        if value is not None and (not isinstance(value, int) or not (min_val <= value <= max_val)):
            errors.append(f"metrics.{field_name} must be between {min_val} and {max_val}")

    return errors


def merge_config_with_defaults(user_config: Dict) -> Dict:
    """
    Merge user configuration with defaults, ensuring all required fields are present.

    Args:
        user_config: User-provided configuration dictionary

    Returns:
        Merged configuration with defaults filled in
    """
    default_config = get_default_operation_config()

    def deep_merge(default: Dict, user: Dict) -> Dict:
        """Recursively merge user config into default config."""
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    return deep_merge(default_config, user_config)


def create_minimal_config() -> Dict:
    """
    Create minimal configuration suitable for testing or lightweight usage.

    Returns:
        Minimal configuration dictionary
    """
    config = get_default_operation_config()

    # Reduce buffer sizes and timeouts for minimal usage
    config["logging"].update(
        {"buffer_size": 100, "flush_interval": 1.0, "operation_timeout": 60.0, "max_operation_depth": 5}
    )

    config["tabular"].update({"max_rows_per_table": 10, "max_table_width": 80})

    config["metrics"].update({"collect_memory_metrics": False, "collect_cpu_metrics": False, "max_custom_metrics": 10})

    return config


def create_performance_config() -> Dict:
    """
    Create configuration optimized for performance.

    Returns:
        Performance-optimized configuration dictionary
    """
    config = get_default_operation_config()

    # Optimize for performance
    config["logging"].update(
        {"buffer_size": 2000, "flush_interval": 0.5, "enable_async_logging": True, "detail_level": "minimal"}
    )

    config["tabular"].update(
        {
            "enabled": False,  # Disable for performance
            "compact_mode": True,
        }
    )

    config["metrics"].update(
        {"collect_memory_metrics": False, "collect_cpu_metrics": False, "compress_large_data": True}
    )

    return config


def get_config_schema() -> Dict:
    """
    Get the configuration schema for validation and documentation.

    Returns:
        Dictionary describing the configuration schema
    """
    return {
        "logging": {
            "operation_time_frame": {"type": "float", "min": 0, "description": "Time frame for operation grouping"},
            "cascade_window": {"type": "float", "min": 0, "description": "Time window for cascade detection"},
            "operation_timeout": {"type": "float", "min": 0, "description": "Timeout for operations"},
            "detail_level": {"type": "enum", "values": ["minimal", "normal", "detailed", "debug"]},
            "buffer_size": {"type": "int", "min": 1, "max": 100000, "description": "Log buffer size"},
            "flush_interval": {"type": "float", "min": 0.1, "max": 3600, "description": "Buffer flush interval"},
        },
        "tabular": {
            "enabled": {"type": "bool", "description": "Enable tabular formatting"},
            "max_table_width": {"type": "int", "min": 50, "description": "Maximum table width"},
            "max_rows_per_table": {"type": "int", "min": 1, "description": "Maximum rows per table"},
            "format_style": {"type": "enum", "values": ["grid", "simple", "plain", "pipe"]},
        },
        "metrics": {
            "collect_timing_metrics": {"type": "bool", "description": "Collect timing metrics"},
            "max_custom_metrics": {"type": "int", "min": 0, "description": "Maximum custom metrics"},
        },
    }


# =============================================================================
# LEGACY FUNCTIONS FOR JSON LOADING (kept for compatibility)
# =============================================================================
# These functions maintain compatibility with existing code that expects
# to load from JSON files, but now use the embedded configuration.


def load_operation_logging_config(config_path: Optional[str] = None) -> Dict:
    """
    Load operation logging configuration.

    If config_path is provided and the file exists, loads from file.
    Otherwise, returns the default embedded configuration.

    Args:
        config_path: Path to configuration file (optional)

    Returns:
        Dictionary containing configuration data
    """
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Fall back to default if file is corrupted
            pass

    # Return embedded default configuration
    return get_default_operation_config()


def apply_json_config_to_tabular_formatting(config_data: Dict) -> TabularFormattingConfig:
    """
    Apply configuration data to TabularFormattingConfig.

    Args:
        config_data: Configuration dictionary (from JSON or embedded default)

    Returns:
        Updated TabularFormattingConfig instance
    """
    tabular_config = TabularFormattingConfig()

    if "tabular" in config_data:
        tabular_section = config_data["tabular"]

        # Map configuration keys to TabularFormattingConfig attributes
        if "enabled" in tabular_section:
            tabular_config.enabled = tabular_section["enabled"]
        if "max_table_width" in tabular_section:
            tabular_config.max_table_width = tabular_section["max_table_width"]
        if "max_rows_per_table" in tabular_section:
            tabular_config.max_rows_per_table = tabular_section["max_rows_per_table"]
        if "ascii_only" in tabular_section:
            tabular_config.ascii_tables = tabular_section["ascii_only"]
        if "show_summary" in tabular_section:
            tabular_config.include_summaries = tabular_section["show_summary"]
        if "priority_tables" in tabular_section:
            tabular_config.priority_tables = tabular_section["priority_tables"]

    return tabular_config


def apply_json_config_to_operation_aggregation(config_data: Dict) -> OperationAggregationConfig:
    """
    Apply configuration data to OperationAggregationConfig.

    Args:
        config_data: Configuration dictionary (from JSON or embedded default)

    Returns:
        Updated OperationAggregationConfig instance
    """
    aggregation_config = OperationAggregationConfig()

    if "logging" in config_data:
        logging_section = config_data["logging"]

        # Map configuration keys to OperationAggregationConfig attributes
        if "aggregate_nested_operations" in logging_section:
            aggregation_config.enabled = logging_section["aggregate_nested_operations"]
        if "cascade_window" in logging_section:
            aggregation_config.cascade_window = logging_section["cascade_window"]

    return aggregation_config


def apply_json_config_to_operation_monitor(config_data: Dict) -> OperationMonitoringConfig:
    """
    Apply configuration data to OperationMonitoringConfig.

    Args:
        config_data: Configuration dictionary (from JSON or embedded default)

    Returns:
        Updated OperationMonitoringConfig instance
    """
    monitor_config = OperationMonitoringConfig()

    if "logging" in config_data:
        logging_section = config_data["logging"]

        # Map configuration keys to OperationMonitoringConfig attributes
        if "operation_timeout" in logging_section:
            monitor_config.operation_timeout_seconds = logging_section["operation_timeout"]
        if "include_performance_metrics" in logging_section:
            monitor_config.enable_performance_tracking = logging_section["include_performance_metrics"]

    if "metrics" in config_data:
        metrics_section = config_data["metrics"]
        if "track_file_operations" in metrics_section:
            monitor_config.enable_memory_tracking = metrics_section["track_file_operations"]

    return monitor_config


def create_config_from_json(config_path: Optional[str] = None) -> Dict:
    """
    Create complete configuration from embedded defaults or JSON file.

    Args:
        config_path: Path to configuration file (optional)

    Returns:
        Dictionary containing all configuration objects
    """
    config_data = load_operation_logging_config(config_path)

    return {
        "tabular_formatting": apply_json_config_to_tabular_formatting(config_data),
        "operation_aggregation": apply_json_config_to_operation_aggregation(config_data),
        "operation_monitoring": apply_json_config_to_operation_monitor(config_data),
        "raw_json": config_data,
    }


def get_default_config_path() -> Path:
    """
    Get the default configuration file path (legacy function).

    Note: This path is no longer required as configuration is embedded,
    but kept for compatibility.

    Returns:
        Path where configuration file would be located
    """
    return Path(__file__).parent.parent.parent / "config" / "operation_logging_config.json"


# =============================================================================
# CONFIGURATION ACCESS HELPERS
# =============================================================================


def get_logging_config(config: Dict = None) -> Dict:
    """Get logging section of configuration."""
    if config is None:
        config = get_default_operation_config()
    return config.get("logging", {})


def get_tabular_config(config: Dict = None) -> Dict:
    """Get tabular section of configuration."""
    if config is None:
        config = get_default_operation_config()
    return config.get("tabular", {})


def get_metrics_config(config: Dict = None) -> Dict:
    """Get metrics section of configuration."""
    if config is None:
        config = get_default_operation_config()
    return config.get("metrics", {})
