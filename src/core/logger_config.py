import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class LoggerManager:
    """Centralized logger configuration manager following best practices."""

    _configured = False
    _root_logger_name = "solid_state_kinetics"
    _aggregating_handlers = []  # Store references to aggregating handlers

    @classmethod
    def configure_logging(  # noqa: C901
        cls,
        log_level: int = logging.DEBUG,
        console_level: Optional[int] = None,
        file_level: Optional[int] = None,
        log_file: Optional[str] = None,
        aggregated_log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_aggregation: bool = False,
        aggregation_config: Optional[dict] = None,
        enable_error_expansion: bool = True,
        enable_tabular_format: bool = True,
        enable_operation_aggregation: bool = True,
        enable_value_aggregation: bool = True,
        aggregation_preset: str = "default",
    ) -> None:
        """
        Configure application-wide logging with both console and file handlers.

        Args:
            log_level: Default logging level for all handlers
            console_level: Specific level for console output (defaults to log_level)
            file_level: Specific level for file output (defaults to DEBUG)
            log_file: Path to main log file (defaults to logs/solid_state_kinetics.log)
            aggregated_log_file: Path to aggregated log file (defaults to logs/aggregated.log)
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            enable_aggregation: Whether to enable log aggregation
            aggregation_config: Configuration dict for log aggregation
        """
        if cls._configured:
            return

        # Set default levels
        console_level = console_level or log_level
        file_level = file_level or logging.DEBUG

        # Get or create root logger for the application
        root_logger = logging.getLogger(cls._root_logger_name)
        root_logger.setLevel(logging.DEBUG)

        # Clear any existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%H:%M:%S"
        )  # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)

        # File handler with rotation (main file - gets ALL logs)
        if log_file is None:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            log_file = logs_dir / "solid_state_kinetics.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Aggregated file handler (only aggregated logs)
        if aggregated_log_file is None:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            aggregated_log_file = logs_dir / "aggregated.log"

        aggregated_file_handler = logging.handlers.RotatingFileHandler(
            aggregated_log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )
        aggregated_file_handler.setLevel(file_level)
        aggregated_file_handler.setFormatter(detailed_formatter)

        # Log aggregation handler
        if enable_aggregation:
            try:
                from src.log_aggregator import AggregatingHandler, AggregationConfig

                # Create aggregation configuration based on preset
                if aggregation_preset == "minimal":
                    agg_config = AggregationConfig.create_minimal()
                elif aggregation_preset == "performance":
                    agg_config = AggregationConfig.create_performance()
                elif aggregation_preset == "detailed":
                    agg_config = AggregationConfig.create_detailed()
                else:
                    agg_config = AggregationConfig()  # Override with specific parameters
                if aggregation_config:
                    # Update config with provided values
                    for key, value in aggregation_config.items():
                        if hasattr(agg_config, key):
                            setattr(agg_config, key, value)

                # Update component configurations
                if agg_config.error_expansion:
                    agg_config.error_expansion.enabled = enable_error_expansion
                if agg_config.tabular_formatting:
                    agg_config.tabular_formatting.enabled = enable_tabular_format
                if agg_config.operation_aggregation:
                    agg_config.operation_aggregation.enabled = enable_operation_aggregation
                if agg_config.value_aggregation:
                    agg_config.value_aggregation.enabled = enable_value_aggregation

                # Create aggregating handlers for both console and aggregated file
                console_aggregating_handler = AggregatingHandler(
                    target_handler=console_handler,
                    config=agg_config,
                    enable_error_expansion=enable_error_expansion,
                    enable_tabular_formatting=enable_tabular_format,
                    enable_operation_aggregation=enable_operation_aggregation,
                    enable_value_aggregation=enable_value_aggregation,
                )
                console_aggregating_handler.setLevel(console_level)
                console_aggregating_handler.setFormatter(console_formatter)

                aggregated_file_aggregating_handler = AggregatingHandler(
                    target_handler=aggregated_file_handler,
                    config=agg_config,
                    enable_error_expansion=enable_error_expansion,
                    enable_tabular_formatting=enable_tabular_format,
                    enable_operation_aggregation=enable_operation_aggregation,
                    enable_value_aggregation=enable_value_aggregation,
                )
                aggregated_file_aggregating_handler.setLevel(file_level)
                aggregated_file_aggregating_handler.setFormatter(detailed_formatter)

                # Add console aggregating handler (console shows only aggregated logs)
                root_logger.addHandler(console_aggregating_handler)
                # Add aggregated file aggregating handler (aggregated file shows only aggregated logs)
                root_logger.addHandler(aggregated_file_aggregating_handler)

                # Store references for runtime management
                cls._aggregating_handlers.append(console_aggregating_handler)
                cls._aggregating_handlers.append(aggregated_file_aggregating_handler)

                root_logger.info(f"Log aggregation enabled with preset: {aggregation_preset}")
                root_logger.info(f"Error expansion: {enable_error_expansion}")
                root_logger.info(f"Tabular formatting: {enable_tabular_format}")
                root_logger.info(f"Operation aggregation: {enable_operation_aggregation}")
                root_logger.info(f"Value aggregation: {enable_value_aggregation}")

                # Setup separate debug logging for internal aggregator logs (Stage 2)
                cls._setup_debug_aggregator_logging()
                root_logger.info("Debug aggregator logging configured")
            except Exception as e:
                root_logger.error(f"Failed to configure log aggregation: {e}")
                # Fallback: add non-aggregating console handler
                root_logger.addHandler(console_handler)
        else:
            # If aggregation is disabled, add console handler directly
            root_logger.addHandler(console_handler)

        # Log the configuration
        root_logger.info("Logging configured successfully")
        console_level_name = logging.getLevelName(console_level)
        root_logger.info(f"Console level: {console_level_name}")
        file_level_name = logging.getLevelName(file_level)
        root_logger.info(f"File level: {file_level_name}")
        root_logger.info(f"Main log file: {log_file}")
        if enable_aggregation:
            root_logger.info(f"Aggregated log file: {aggregated_log_file}")
            root_logger.info("Console output: aggregated logs only")
            root_logger.info("Main file: all logs (raw + aggregated)")
            root_logger.info("Aggregated file: aggregated logs only")

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for the specified module.

        Args:
            name: Logger name (typically __name__ of the module)

        Returns:
            Configured logger instance
        """
        # Ensure logging is configured
        if not cls._configured:
            cls.configure_logging()

        # Clean up module name for better readability
        clean_name = cls._clean_module_name(name)

        # Return child logger of the application root logger
        if clean_name.startswith(cls._root_logger_name):
            return logging.getLogger(clean_name)
        else:
            return logging.getLogger(f"{cls._root_logger_name}.{clean_name}")

    @classmethod
    def _clean_module_name(cls, module_name: str) -> str:
        """
        Clean module name to make it more readable in logs.

        Examples:
        - 'src.gui.main_window' -> 'gui.main_window'
        - 'src.core.base_signals' -> 'core.base_signals'
        - '__main__' -> 'main'
        """
        if module_name == "__main__":
            return "main"

        # Remove 'src.' prefix if present
        if module_name.startswith("src."):
            return module_name[4:]  # Remove full path prefixes like 'solid_state_kinetics.src.'
        if "src." in module_name:
            parts = module_name.split("src.")
            if len(parts) > 1:
                return parts[-1]

        return module_name

    @classmethod
    def toggle_aggregation(cls, enabled: bool) -> None:
        """Enable/disable aggregation in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "enabled"):
                handler.enabled = enabled

    @classmethod
    def toggle_error_expansion(cls, enabled: bool) -> None:
        """Enable/disable error expansion in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "enable_error_expansion"):
                handler.enable_error_expansion = enabled

    @classmethod
    def toggle_tabular_format(cls, enabled: bool) -> None:
        """Enable/disable tabular formatting in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "enable_tabular_formatting"):
                handler.enable_tabular_formatting = enabled

    @classmethod
    def toggle_operation_aggregation(cls, enabled: bool) -> None:
        """Enable/disable operation aggregation in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "enable_operation_aggregation"):
                handler.enable_operation_aggregation = enabled

    @classmethod
    def toggle_value_aggregation(cls, enabled: bool) -> None:
        """Enable/disable value aggregation in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "enable_value_aggregation"):
                handler.enable_value_aggregation = enabled

    @classmethod
    def get_aggregation_stats(cls) -> dict:
        """Get extended aggregation statistics including aggregators."""
        combined_stats = {
            "handlers": {},
            "total_stats": {
                "total_records": 0,
                "aggregated_records": 0,
                "patterns_detected": 0,
                "errors_expanded": 0,
                "tables_generated": 0,
                "buffer_flushes": 0,
                "operation_cascades_aggregated": 0,
                "values_compressed": 0,
                "cache_hits_on_errors": 0,
            },
        }

        for i, handler in enumerate(cls._aggregating_handlers):
            handler_stats = {}
            if hasattr(handler, "get_statistics"):
                handler_stats = handler.get_statistics()
            elif hasattr(handler, "stats"):
                handler_stats = handler.stats

            combined_stats["handlers"][f"handler_{i}"] = handler_stats

            # Aggregate totals
            for key in combined_stats["total_stats"]:
                if key in handler_stats:
                    combined_stats["total_stats"][key] += handler_stats[key]

        # Calculate derived metrics
        total_processed = combined_stats["total_stats"]["total_records"]
        if total_processed > 0:
            combined_stats["total_stats"]["compression_ratio"] = (
                1 - combined_stats["total_stats"]["aggregated_records"] / total_processed
            )
            combined_stats["total_stats"]["error_expansion_ratio"] = (
                combined_stats["total_stats"]["errors_expanded"] / total_processed
            )
            combined_stats["total_stats"]["operation_compression_ratio"] = (
                combined_stats["total_stats"]["operation_cascades_aggregated"] / total_processed
            )
            combined_stats["total_stats"]["value_compression_ratio"] = (
                combined_stats["total_stats"]["values_compressed"] / total_processed
            )

        return combined_stats

    @classmethod
    def export_aggregation_config(cls) -> dict:
        """Export current aggregation configuration."""
        config_data = {}
        for i, handler in enumerate(cls._aggregating_handlers):
            if hasattr(handler, "config"):
                if hasattr(handler.config, "to_dict"):
                    config_data[f"handler_{i}"] = handler.config.to_dict()
                else:
                    config_data[f"handler_{i}"] = str(handler.config)
        return config_data

    @classmethod
    def update_aggregation_config(cls, config_updates: dict) -> None:  # noqa: C901
        """Update aggregation configuration in runtime."""
        for handler in cls._aggregating_handlers:
            if hasattr(handler, "config"):
                # Update basic configuration fields
                for key, value in config_updates.items():
                    if hasattr(handler.config, key):
                        setattr(handler.config, key, value)

                # Update component configurations
                if "operation_aggregation" in config_updates and hasattr(handler.config, "operation_aggregation"):
                    op_config = config_updates["operation_aggregation"]
                    for key, value in op_config.items():
                        if hasattr(handler.config.operation_aggregation, key):
                            setattr(handler.config.operation_aggregation, key, value)

                if "value_aggregation" in config_updates and hasattr(handler.config, "value_aggregation"):
                    val_config = config_updates["value_aggregation"]
                    for key, value in val_config.items():
                        if hasattr(handler.config.value_aggregation, key):
                            setattr(handler.config.value_aggregation, key, value)

    @classmethod
    def _setup_debug_aggregator_logging(cls):
        """Setup separate debug logging for aggregator internals."""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        debug_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "debug_aggregator.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        debug_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        debug_handler.setFormatter(debug_formatter)

        # Setup internal loggers with no propagation to prevent recursion
        internal_loggers = [
            "log_aggregator.realtime_handler",
            "log_aggregator.pattern_detector",
            "log_aggregator.error_expansion",
            "log_aggregator.value_aggregator",
            "log_aggregator.operation_aggregator",
            "log_aggregator.tabular_formatter",
            "log_aggregator.buffer_manager",
            "log_aggregator.aggregation_engine",
        ]

        for logger_name in internal_loggers:
            logger = logging.getLogger(logger_name)
            logger.propagate = False  # Prevent recursion
            logger.addHandler(debug_handler)
            logger.setLevel(logging.DEBUG)


def configure_logger(log_level: int = logging.INFO) -> logging.Logger:
    """
    Legacy function for backward compatibility with existing code.

    Args:
        log_level: Logging level (now affects console output level)

    Returns:
        Configured logger instance
    """
    # Configure logging if not already done
    LoggerManager.configure_logging(console_level=log_level)

    # Return a logger for the calling module
    import inspect

    frame = inspect.currentframe().f_back
    module_name = frame.f_globals.get("__name__", "unknown")

    return LoggerManager.get_logger(module_name)


# Initialize logging on module import with aggregation enabled
LoggerManager.configure_logging(
    enable_aggregation=True,
    aggregation_preset="performance",
    enable_error_expansion=True,
    enable_tabular_format=True,
    enable_operation_aggregation=True,
    enable_value_aggregation=True,
)


# Provide default logger instance for backward compatibility
# This creates a factory function that returns proper logger for each module
def get_module_logger():
    """Get a logger for the calling module."""
    import inspect

    frame = inspect.currentframe().f_back
    module_name = frame.f_globals.get("__name__", "unknown")
    return LoggerManager.get_logger(module_name)


# For backward compatibility, create a logger that appears to be from this module
logger = LoggerManager.get_logger("core.logger_config")
