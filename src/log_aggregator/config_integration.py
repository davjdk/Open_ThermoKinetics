"""
Configuration integration utilities for operation logging system.

This module provides utilities to apply configuration settings to various
components of the operation logging system including loggers, aggregators,
and formatters.
"""

import logging
from typing import Optional

from .operation_config_manager import get_metrics_config, get_operation_config, get_tabular_config

logger = logging.getLogger(__name__)


def apply_timing_configuration(operation_logger=None, aggregator=None) -> None:
    """
    Apply timing configuration to operation logging components.

    Args:
        operation_logger: OperationLogger instance to configure
        aggregator: OperationAggregator instance to configure
    """
    try:
        config = get_operation_config()
        _apply_logger_timing(operation_logger, config)
        _apply_aggregator_timing(aggregator, config)
        logger.info(f"Applied timing configuration: timeout={config.operation_timeout}s")
    except Exception as e:
        logger.error(f"Failed to apply timing configuration: {e}")


def _apply_logger_timing(operation_logger, config) -> None:
    """Apply timing configuration to operation logger."""
    if operation_logger and hasattr(operation_logger, "_operation_timeout"):
        operation_logger._operation_timeout = config.operation_timeout
        operation_logger._nested_timeout = config.nested_operation_timeout


def _apply_aggregator_timing(aggregator, config) -> None:
    """Apply timing configuration to aggregator."""
    if aggregator:
        if hasattr(aggregator, "config"):
            if hasattr(aggregator.config, "cascade_window"):
                aggregator.config.cascade_window = config.cascade_window
            if hasattr(aggregator.config, "operation_aggregation"):
                aggregator.config.operation_aggregation.cascade_window = config.cascade_window

        # Apply grouping settings
        if config.enable_operation_grouping:
            if hasattr(aggregator, "enable_grouping"):
                aggregator.enable_grouping()
            if config.group_by_thread and hasattr(aggregator, "set_group_by_thread"):
                aggregator.set_group_by_thread(True)
        else:
            if hasattr(aggregator, "disable_grouping"):
                aggregator.disable_grouping()


def apply_tabular_configuration(tabular_formatter=None) -> None:
    """
    Apply tabular formatting configuration.

    Args:
        tabular_formatter: TabularFormatter instance to configure
    """
    try:
        config = get_tabular_config()

        if tabular_formatter and config:
            # Apply table format
            if hasattr(tabular_formatter, "table_format"):
                tabular_formatter.table_format = config.format_style

            # Apply formatting options
            if hasattr(tabular_formatter, "max_width"):
                tabular_formatter.max_width = config.max_table_width

            logger.info(
                f"Applied tabular configuration: format={config.format_style}, "
                f"width={config.max_table_width}, ascii_only={config.ascii_only}"
            )

    except Exception as e:
        logger.warning(f"Failed to apply tabular configuration: {e}")


def apply_metrics_configuration(metrics_collector=None) -> None:
    """
    Apply metrics collection configuration.

    Args:
        metrics_collector: Metrics collector instance to configure
    """
    try:
        config = get_metrics_config()

        if metrics_collector and config:
            # Apply basic metrics settings
            if hasattr(metrics_collector, "collect_timing"):
                metrics_collector.collect_timing = config.collect_timing_metrics
            if hasattr(metrics_collector, "collect_memory"):
                metrics_collector.collect_memory = config.collect_memory_metrics
            if hasattr(metrics_collector, "collect_cpu"):
                metrics_collector.collect_cpu = config.collect_cpu_metrics

            # Apply file operation tracking
            if hasattr(metrics_collector, "track_files"):
                metrics_collector.track_files = config.track_file_operations

            # Apply compression settings
            if hasattr(metrics_collector, "compression_config"):
                compression_config = metrics_collector.compression_config
                if hasattr(compression_config, "enabled"):
                    compression_config.enabled = config.compress_large_data
                    compression_config.array_threshold = config.array_compression_threshold
                    compression_config.dataframe_threshold = config.dataframe_compression_threshold
                    compression_config.string_threshold = config.string_compression_threshold

            logger.info(
                f"Applied metrics configuration: "
                f"compression={'enabled' if config.compress_large_data else 'disabled'}, "
                f"array_threshold={config.array_compression_threshold}"
            )

    except Exception as e:
        logger.warning(f"Failed to apply metrics configuration: {e}")


def create_configured_operation_logger(**kwargs) -> Optional[object]:
    """
    Create an operation logger with current configuration applied.

    Args:
        **kwargs: Additional arguments for OperationLogger constructor

    Returns:
        Configured OperationLogger instance or None if creation fails
    """
    try:
        from .operation_logger import OperationLogger

        # Get configuration
        tabular_config = get_tabular_config()

        # Create logger with configuration
        operation_logger = OperationLogger(enable_tables=tabular_config.enabled if tabular_config else True, **kwargs)

        # Apply configurations
        apply_timing_configuration(operation_logger)
        apply_tabular_configuration(getattr(operation_logger, "tabular_formatter", None))

        return operation_logger

    except Exception as e:
        logger.error(f"Failed to create configured operation logger: {e}")
        return None


def load_configuration_from_file(config_path: str) -> bool:
    """
    Load configuration from file and apply to all components.

    Args:
        config_path: Path to configuration file

    Returns:
        True if configuration was loaded successfully, False otherwise
    """
    try:
        from .operation_config_manager import config_manager

        # Load configuration from file
        config_manager.load_from_file(config_path)

        logger.info(f"Configuration loaded from {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        return False


def save_current_configuration(config_path: str) -> bool:
    """
    Save current configuration to file.

    Args:
        config_path: Path to save configuration file

    Returns:
        True if configuration was saved successfully, False otherwise
    """
    try:
        from .operation_config_manager import config_manager

        # Save current configuration to file
        config_manager.save_to_file(config_path)

        logger.info(f"Configuration saved to {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {e}")
        return False


def validate_current_configuration() -> bool:
    """
    Validate current configuration.

    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        from .operation_config_manager import config_manager

        errors = config_manager.validate_configuration()
        if errors:
            logger.warning(f"Configuration validation errors: {errors}")
            return False

        logger.info("Configuration validation successful")
        return True

    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        return False


def apply_all_configurations(operation_logger=None, aggregator=None, tabular_formatter=None, metrics_collector=None):
    """
    Apply all current configurations to provided components.

    Args:
        operation_logger: OperationLogger instance to configure
        aggregator: OperationAggregator instance to configure
        tabular_formatter: TabularFormatter instance to configure
        metrics_collector: Metrics collector instance to configure
    """
    try:
        apply_timing_configuration(operation_logger, aggregator)
        apply_tabular_configuration(tabular_formatter)
        apply_metrics_configuration(metrics_collector)

        logger.info("Applied all configurations successfully")

    except Exception as e:
        logger.error(f"Failed to apply configurations: {e}")
