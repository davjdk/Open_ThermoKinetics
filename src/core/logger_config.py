import logging
import logging.handlers
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .log_aggregator.formatter_config import FormatterConfig


class LoggerManager:
    """Centralized logger configuration manager following best practices."""

    _configured = False
    _root_logger_name = "solid_state_kinetics"

    @classmethod
    def configure_logging(
        cls,
        log_level: int = logging.DEBUG,
        console_level: Optional[int] = None,
        file_level: Optional[int] = None,
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ) -> None:
        """
        Configure application-wide logging with both console and file handlers.

        Args:
            log_level: Default logging level for all handlers
            console_level: Specific level for console output (defaults to log_level)
            file_level: Specific level for file output (defaults to DEBUG)
            log_file: Path to log file (defaults to logs/solid_state_kinetics.log)
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
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
        root_logger.handlers.clear()  # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation
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

        # Log the configuration
        root_logger.info("Logging configured successfully")
        console_level_name = logging.getLevelName(console_level)
        root_logger.info(f"Console level: {console_level_name}")
        file_level_name = logging.getLevelName(file_level)
        root_logger.info(f"File level: {file_level_name}")
        root_logger.info(f"Log file: {log_file}")

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
            return module_name[4:]

        # Remove full path prefixes like 'solid_state_kinetics.src.'
        if "src." in module_name:
            parts = module_name.split("src.")
            if len(parts) > 1:
                return parts[-1]

        return module_name


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


# Initialize logging on module import
LoggerManager.configure_logging()


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

# Configuration for meta-operation detection system
META_OPERATION_CONFIG = {
    "enabled": True,  # Global enable/disable flag
    "debug_mode": False,  # Detailed logging of meta-operation detection
    "strategies": {
        "time_window": {"enabled": True, "config": {"time_window_ms": 50.0}},
        "target_cluster": {
            "enabled": True,
            "config": {
                "target_list": ["file_data", "series_data", "calculation_data"],
                "max_gap": 1,
                "strict_sequence": False,
            },
        },
        "name_similarity": {
            "enabled": True,
            "config": {"name_pattern": "GET_.*|SET_.*|UPDATE_.*", "prefix_length": 3, "case_sensitive": False},
        },
        "sequence_count": {
            "enabled": False,  # Disable for now
            "config": {"min_sequence": 3, "max_gap": 0},
        },
        "frequency_threshold": {
            "enabled": False,  # Disable for now
            "config": {"freq_threshold": 5, "freq_window_ms": 1000.0},
        },
    },  # Formatting settings for meta-operations display
    "formatting": {
        "group_meta_operations": True,  # Include grouping in output
        "compact_meta_view": True,  # Compact display
        "show_individual_ops": False,  # Show operations within groups
        "max_operations_inline": 5,  # Maximum operations inline
        "meta_operation_symbol": "►",  # Symbol for meta-operations
        "indent_size": 2,  # Indent size for nested operations
        # Additional options
        "show_meta_statistics": True,  # Show statistics for groups
        "highlight_errors": True,  # Highlight errors in groups
        "time_precision": 3,  # Time precision (decimal places)
        # Output modes configuration
        "output_modes": {
            "default": "compact",  # Default mode
            "debug": "expanded",  # Debug mode
            "json": False,  # Additional JSON output
        },
    },
    # Display filters
    "display_filters": {
        "min_group_size": 2,  # Minimum group size for display
        "max_group_size": 50,  # Maximum size for expanded display
        "hide_successful_groups": False,  # Hide fully successful groups
        "hide_single_operations": False,  # Hide single operations
    },
}


def create_formatter_config_from_meta_config() -> "FormatterConfig":
    """
    Create FormatterConfig instance from META_OPERATION_CONFIG.

    Returns:
        FormatterConfig: Configured instance based on META_OPERATION_CONFIG
    """
    from .log_aggregator.formatter_config import FormatterConfig

    formatting_config = META_OPERATION_CONFIG.get("formatting", {})
    display_filters = META_OPERATION_CONFIG.get("display_filters", {})

    return FormatterConfig(
        # Basic parameters
        table_format="grid",
        max_cell_width=50,
        include_error_details=True,
        max_error_context_items=5,
        # Meta-operations parameters from config
        group_meta_operations=formatting_config.get("group_meta_operations", True),
        compact_meta_view=formatting_config.get("compact_meta_view", True),
        show_individual_ops=formatting_config.get("show_individual_ops", False),
        max_operations_inline=formatting_config.get("max_operations_inline", 5),
        meta_operation_symbol=formatting_config.get("meta_operation_symbol", "►"),
        indent_size=formatting_config.get("indent_size", 2),
        # Additional options
        show_meta_statistics=formatting_config.get("show_meta_statistics", True),
        highlight_errors=formatting_config.get("highlight_errors", True),
        time_precision=formatting_config.get("time_precision", 3),
        # Output modes and display filters
        output_modes=formatting_config.get("output_modes", {}),
        display_filters=display_filters,
    )
