"""
Centralized configuration system for operation logging and aggregation.

This module provides comprehensive configuration management for the operation
logging system including timing parameters, table formatting, metrics collection,
and error handling settings.
"""

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List

from .config import OperationAggregationConfig


@dataclass
class OperationLoggingConfig:
    """Comprehensive configuration for operation logging system."""

    # Temporal parameters
    operation_time_frame: float = 1.0  # Operation grouping window (seconds)
    cascade_window: float = 1.0  # Cascade operation window (seconds)
    operation_timeout: float = 300.0  # Operation timeout (seconds)
    nested_operation_timeout: float = 60.0  # Nested operation timeout (seconds)

    # Aggregation parameters
    aggregate_nested_operations: bool = True  # Aggregate nested operations
    max_operation_depth: int = 10  # Maximum nesting depth
    enable_operation_grouping: bool = True  # Enable operation grouping
    group_by_thread: bool = True  # Group by thread

    # Table formatting (Tabulate-based)
    tabulate_enabled: bool = True  # Enable tabulate formatting
    tabulate_format: str = "grid"  # Table format: grid/simple/plain/pipe
    force_ascii_tables: bool = True  # Force ASCII tables for logs
    table_max_width: int = 120  # Maximum table width
    table_headers: bool = True  # Show table headers

    # Tabulate table styles
    table_grid_style: str = "grid"  # grid/fancy_grid/simple/plain/pipe
    table_number_alignment: str = "right"  # Number column alignment
    table_text_alignment: str = "left"  # Text column alignment
    show_table_headers: bool = True  # Show column headers

    # Status symbols and formatting
    use_unicode_symbols: bool = True  # ✅/❌ symbols vs [OK]/[ERR]
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"  # Timestamp format
    duration_precision: int = 3  # Duration decimal places
    max_error_message_length: int = 100  # Max error message length

    # Detail levels
    detail_level: str = "normal"  # minimal/normal/detailed/debug
    include_user_metrics: bool = True  # Include user-defined metrics
    include_file_metrics: bool = True  # Include file operation metrics
    include_performance_metrics: bool = True  # Include performance metrics

    # Operation filtering
    exclude_operations: List[str] = field(default_factory=list)  # Excluded operations
    include_only_operations: List[str] = field(default_factory=list)  # Only these operations
    min_operation_duration: float = 0.0  # Minimum duration for logging

    # Error handling
    log_full_traceback: bool = False  # Log full traceback
    auto_recovery_enabled: bool = True  # Enable auto-recovery
    max_recovery_attempts: int = 3  # Maximum recovery attempts

    # Performance settings
    enable_async_logging: bool = False  # Asynchronous logging
    buffer_size: int = 1000  # Log buffer size
    flush_interval: float = 5.0  # Buffer flush interval (seconds)


@dataclass
class TabularFormattingConfig:
    """Configuration for tabulate-based table formatting."""

    # Core tabulate settings
    enabled: bool = True  # Enable tabular formatting
    format_style: str = "grid"  # Tabulate format style
    headers_enabled: bool = True  # Show table headers
    max_table_width: int = 120  # Maximum table width
    max_rows_per_table: int = 20  # Maximum rows per table

    # Column formatting
    property_column_width: int = 20  # Property column width
    value_column_width: int = 40  # Value column width
    number_format: str = ".3f"  # Number formatting
    align_numbers: str = "right"  # Number alignment
    align_text: str = "left"  # Text alignment

    # Display options
    show_summary: bool = True  # Show summary below tables
    compact_mode: bool = False  # Compact table display
    ascii_only: bool = True  # Force ASCII characters only

    # Table priorities
    priority_tables: List[str] = field(
        default_factory=lambda: ["operation_summary", "error_analysis", "cascade_operations"]
    )

    # Status symbols (ASCII-compatible)
    success_symbol: str = "[OK]"  # Success symbol
    error_symbol: str = "[ERR]"  # Error symbol
    timeout_symbol: str = "[TMO]"  # Timeout symbol
    running_symbol: str = "[RUN]"  # Running symbol

    def __post_init__(self):
        """Post-initialization to set Unicode symbols if enabled."""
        if not self.ascii_only:
            self.success_symbol = "✅"
            self.error_symbol = "❌"
            self.timeout_symbol = "⏱️"
            self.running_symbol = "🔄"


@dataclass
class OperationMetricsConfig:
    """Configuration for operation metrics collection."""

    # Basic metrics
    collect_timing_metrics: bool = True  # Collect timing metrics
    collect_memory_metrics: bool = False  # Collect memory metrics
    collect_cpu_metrics: bool = False  # Collect CPU metrics
    collect_io_metrics: bool = True  # Collect I/O metrics

    # File operation metrics
    track_file_operations: bool = True  # Track file operations
    track_file_sizes: bool = True  # Track file sizes
    track_file_modifications: bool = True  # Track file modifications

    # Domain-specific metrics (kinetic analysis)
    track_reaction_metrics: bool = True  # Track reaction metrics
    track_optimization_metrics: bool = True  # Track optimization metrics
    track_convergence_metrics: bool = True  # Track convergence metrics
    track_quality_metrics: bool = True  # Track quality metrics (R², RMSE)

    # Custom metrics
    allow_custom_metrics: bool = True  # Allow custom metrics
    max_custom_metrics: int = 50  # Maximum custom metrics
    custom_metrics_prefix: str = "user_"  # Custom metrics prefix

    # Data compression for metrics
    compress_large_data: bool = True  # Compress large data structures
    array_compression_threshold: int = 10  # Array compression threshold
    dataframe_compression_threshold: int = 5  # DataFrame compression threshold
    string_compression_threshold: int = 200  # String compression threshold


class OperationConfigManager:
    """Centralized configuration manager for operation logging system."""

    def __init__(self):
        """Initialize configuration manager with default settings."""
        self._logging_config = OperationLoggingConfig()
        self._tabular_config = TabularFormattingConfig()
        self._metrics_config = OperationMetricsConfig()
        self._observers: List[Callable] = []
        self._lock = threading.Lock()

        # Load configuration from environment variables
        self._load_from_environment()

    def get_logging_config(self) -> OperationLoggingConfig:
        """Get current logging configuration."""
        return self._logging_config

    def get_tabular_config(self) -> TabularFormattingConfig:
        """Get current tabular formatting configuration."""
        return self._tabular_config

    def get_metrics_config(self) -> OperationMetricsConfig:
        """Get current metrics collection configuration."""
        return self._metrics_config

    def update_config(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.

        Args:
            config_dict: Dictionary with configuration updates
        """
        with self._lock:
            for key, value in config_dict.items():
                if hasattr(self._logging_config, key):
                    setattr(self._logging_config, key, value)
                    self._notify_observers("logging", key, value)
                elif hasattr(self._tabular_config, key):
                    setattr(self._tabular_config, key, value)
                    self._notify_observers("tabular", key, value)
                elif hasattr(self._metrics_config, key):
                    setattr(self._metrics_config, key, value)
                    self._notify_observers("metrics", key, value)

    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            self._load_logging_config(config_data)
            self._load_tabular_config(config_data)
            self._load_metrics_config(config_data)

            self._notify_observers("config", "loaded", config_path)

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")

    def _load_logging_config(self, config_data: Dict[str, Any]) -> None:
        """Load logging configuration section."""
        if "logging" not in config_data:
            return

        with self._lock:
            for key, value in config_data["logging"].items():
                if hasattr(self._logging_config, key):
                    setattr(self._logging_config, key, value)

    def _load_tabular_config(self, config_data: Dict[str, Any]) -> None:
        """Load tabular configuration section."""
        if "tabular" not in config_data:
            return

        with self._lock:
            for key, value in config_data["tabular"].items():
                if hasattr(self._tabular_config, key):
                    setattr(self._tabular_config, key, value)

    def _load_metrics_config(self, config_data: Dict[str, Any]) -> None:
        """Load metrics configuration section."""
        if "metrics" not in config_data:
            return

        with self._lock:
            for key, value in config_data["metrics"].items():
                if hasattr(self._metrics_config, key):
                    setattr(self._metrics_config, key, value)

    def save_to_file(self, config_path: str) -> None:
        """
        Save current configuration to JSON file.

        Args:
            config_path: Path to save configuration file
        """
        try:
            config_data = {
                "logging": asdict(self._logging_config),
                "tabular": asdict(self._tabular_config),
                "metrics": asdict(self._metrics_config),
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}")

    def add_observer(self, observer: Callable[[str, str, Any], None]) -> None:
        """
        Add configuration change observer.

        Args:
            observer: Callback function called when configuration changes
        """
        with self._lock:
            self._observers.append(observer)

    def remove_observer(self, observer: Callable[[str, str, Any], None]) -> None:
        """
        Remove configuration change observer.

        Args:
            observer: Observer to remove
        """
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def _notify_observers(self, section: str, key: str, value: Any) -> None:
        """
        Notify observers of configuration changes.

        Args:
            section: Configuration section that changed
            key: Configuration key that changed
            value: New value
        """
        for observer in self._observers:
            try:
                observer(section, key, value)
            except Exception:
                # Don't let observer errors break configuration updates
                pass

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            # Logging configuration
            "SSK_OPERATION_TIME_FRAME": ("logging", "operation_time_frame", float),
            "SSK_CASCADE_WINDOW": ("logging", "cascade_window", float),
            "SSK_OPERATION_TIMEOUT": ("logging", "operation_timeout", float),
            "SSK_DETAIL_LEVEL": ("logging", "detail_level", str),
            "SSK_USE_UNICODE": ("logging", "use_unicode_symbols", bool),
            "SSK_ENABLE_ASYNC": ("logging", "enable_async_logging", bool),
            # Tabular configuration
            "SSK_TABULATE_FORMAT": ("tabular", "format_style", str),
            "SSK_TABLE_MAX_WIDTH": ("tabular", "max_table_width", int),
            "SSK_ASCII_ONLY": ("tabular", "ascii_only", bool),
            "SSK_SHOW_HEADERS": ("tabular", "headers_enabled", bool),
            # Metrics configuration
            "SSK_COLLECT_MEMORY": ("metrics", "collect_memory_metrics", bool),
            "SSK_COLLECT_CPU": ("metrics", "collect_cpu_metrics", bool),
            "SSK_TRACK_FILES": ("metrics", "track_file_operations", bool),
        }

        for env_var, (section, key, value_type) in env_mapping.items():
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

                    if section == "logging":
                        setattr(self._logging_config, key, value)
                    elif section == "tabular":
                        setattr(self._tabular_config, key, value)
                    elif section == "metrics":
                        setattr(self._metrics_config, key, value)

                except (ValueError, TypeError):
                    # Ignore invalid environment variable values
                    pass

    def validate_configuration(self) -> List[str]:
        """
        Validate current configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate logging configuration
        if self._logging_config.operation_time_frame <= 0:
            errors.append("operation_time_frame must be positive")

        if self._logging_config.operation_timeout <= 0:
            errors.append("operation_timeout must be positive")

        if self._logging_config.cascade_window < 0:
            errors.append("cascade_window must be non-negative")

        if self._logging_config.max_operation_depth < 1:
            errors.append("max_operation_depth must be at least 1")

        valid_detail_levels = ["minimal", "normal", "detailed", "debug"]
        if self._logging_config.detail_level not in valid_detail_levels:
            errors.append(f"detail_level must be one of {valid_detail_levels}")

        # Validate tabular configuration
        if self._tabular_config.max_table_width < 50:
            errors.append("max_table_width must be at least 50")

        if self._tabular_config.max_rows_per_table < 1:
            errors.append("max_rows_per_table must be at least 1")

        # Validate metrics configuration
        if self._metrics_config.max_custom_metrics < 0:
            errors.append("max_custom_metrics must be non-negative")

        return errors

    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values."""
        with self._lock:
            self._logging_config = OperationLoggingConfig()
            self._tabular_config = TabularFormattingConfig()
            self._metrics_config = OperationMetricsConfig()

        self._notify_observers("config", "reset", "defaults")

    def get_legacy_aggregation_config(self) -> OperationAggregationConfig:
        """
        Get legacy OperationAggregationConfig for backward compatibility.

        Returns:
            OperationAggregationConfig instance with current settings
        """
        return OperationAggregationConfig(
            enabled=self._logging_config.aggregate_nested_operations,
            cascade_window=self._logging_config.cascade_window,
            min_cascade_size=3,  # Default value
        )

    def get_legacy_tabular_config(self) -> TabularFormattingConfig:
        """
        Get legacy TabularFormattingConfig for backward compatibility.

        Returns:
            TabularFormattingConfig instance with current settings
        """
        return TabularFormattingConfig(
            enabled=self._tabular_config.enabled,
            max_table_width=self._tabular_config.max_table_width,
            max_rows_per_table=self._tabular_config.max_rows_per_table,
            ascii_tables=self._tabular_config.ascii_only,
            include_summaries=self._tabular_config.show_summary,
        )


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


# Global configuration manager instance
config_manager = OperationConfigManager()


def get_operation_config() -> OperationLoggingConfig:
    """Get current operation logging configuration."""
    return config_manager.get_logging_config()


def get_tabular_config() -> TabularFormattingConfig:
    """Get current tabular formatting configuration."""
    return config_manager.get_tabular_config()


def get_metrics_config() -> OperationMetricsConfig:
    """Get current metrics collection configuration."""
    return config_manager.get_metrics_config()


def update_operation_config(**kwargs) -> None:
    """Update operation configuration with keyword arguments."""
    config_manager.update_config(kwargs)


def load_config_from_file(config_path: str) -> None:
    """Load configuration from file."""
    config_manager.load_from_file(config_path)


def save_config_to_file(config_path: str) -> None:
    """Save current configuration to file."""
    config_manager.save_to_file(config_path)
