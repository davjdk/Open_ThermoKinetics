"""
Operation Logger API for explicit operation boundaries marking with decorator support.

This module provides a simplified API for developers to explicitly mark operation
boundaries in code, enabling detailed tracking and analysis of user operations.
Supports automatic tabular output and integrates with @operation decorator.
"""

import logging
import re
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Conditional import to avoid circular dependencies
if TYPE_CHECKING:
    from .operation_monitor import OperationMonitor

# Try to import numpy and pandas for data processing
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

# Import components for explicit mode operation
try:
    from .config import OperationAggregationConfig, TabularFormattingConfig
    from .operation_aggregator import OperationAggregator
    from .operation_error_handler import DefaultOperationErrorHandler, OperationErrorHandler
    from .tabular_formatter import TabularFormatter
except ImportError:
    # Handle case where components are not available
    OperationAggregator = None
    TabularFormatter = None
    TabularFormattingConfig = None
    OperationAggregationConfig = None
    OperationErrorHandler = None
    DefaultOperationErrorHandler = None

try:
    from .operation_config_manager import config_manager

    HAS_CONFIG_MANAGER = True
except ImportError:
    HAS_CONFIG_MANAGER = False
    config_manager = None


@dataclass
class DataCompressionConfig:
    """Configuration for data compression in metrics."""

    enabled: bool = True
    array_threshold: int = 10
    dataframe_threshold: int = 5
    dict_threshold: int = 8
    string_threshold: int = 200

    @property
    def compression_patterns(self):
        """Get regex patterns for data compression."""
        return {
            "numpy_array": re.compile(r"array\(\[([\d\.,\s\-e]+)\]\)"),
            "dataframe": re.compile(r"(temperature|rate_\d+).*?\[(\d+) rows x (\d+) columns\]"),
            "long_string": re.compile(rf"\"([^\"]{{{self.string_threshold},}})\""),
        }


@dataclass
class OperationContext:
    """Context information for a single operation with error tracking."""

    operation_id: str
    operation_name: str
    start_time: datetime
    parent_operation_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "RUNNING"
    end_time: Optional[datetime] = None
    error_info: Optional[Dict[str, Any]] = None
    sub_operations_count: int = 0
    files_modified: int = 0

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def add_error_info(self, exc_type: type, exc_val: Exception, exc_tb=None) -> None:
        """Add error information to context."""
        self.error_info = {
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_val) if exc_val else "Unknown error",
            "traceback": str(exc_tb) if exc_tb else None,
        }
        self.status = "ERROR"


class OperationLogger:
    """
    Main API class for explicit operation logging with automatic tabular output.

    Provides simple methods for marking operation boundaries and collecting
    custom metrics within operations. Integrates with @operation decorator
    and automatically generates ASCII tables after each operation.
    """

    def __init__(
        self,
        logger_name: str = "solid_state_kinetics.operations",
        aggregator=None,
        compression_config: Optional[DataCompressionConfig] = None,
        operation_monitor: Optional["OperationMonitor"] = None,
        enable_tables: bool = True,
        error_handlers: Optional[List] = None,
    ):
        """
        Initialize the operation logger.

        Args:
            logger_name: Name of the logger to use for operation logging
            aggregator: Optional OperationAggregator for integration (explicit mode only)
            compression_config: Configuration for data compression
            operation_monitor: Optional OperationMonitor for enhanced tracking
            enable_tables: Whether to enable automatic ASCII table generation
            error_handlers: List of error handlers to register for error processing
        """
        self.logger = logging.getLogger(logger_name)
        self.compression_config = compression_config or DataCompressionConfig()
        self.operation_monitor = operation_monitor
        self.enable_tables = enable_tables
        self._local = threading.local()  # Initialize components
        self._init_config_manager()
        self._init_error_handlers(error_handlers)
        self._init_aggregator(aggregator)
        self._init_tabular_formatter()

    def _init_config_manager(self):
        """Initialize configuration manager integration."""
        self._config_manager = None
        self._operation_config = None
        self._tabular_config = None
        if HAS_CONFIG_MANAGER and config_manager:
            self._config_manager = config_manager
            self._operation_config = self._config_manager.get_logging_config()
            self._tabular_config = self._config_manager.get_tabular_config()

            # Subscribe to configuration changes
            self._config_manager.add_observer(self._on_config_changed)

            # Override enable_tables with configuration
            if self._tabular_config:
                self.enable_tables = self._tabular_config.enabled

    def _init_error_handlers(self, error_handlers):
        """Initialize error handlers."""
        self._error_handlers: List = []
        self._default_error_handler = None
        if DefaultOperationErrorHandler:
            self._default_error_handler = DefaultOperationErrorHandler()

        # Register custom error handlers
        if error_handlers:
            for handler in error_handlers:
                self.register_error_handler(handler)

    def _init_tabular_formatter(self):
        """Initialize tabular formatter if available and enabled."""
        self.tabular_formatter = None
        if self.enable_tables and TabularFormatter:
            try:
                table_config = TabularFormattingConfig() if TabularFormattingConfig else None
                self.tabular_formatter = TabularFormatter(table_config)
            except Exception as e:
                self.logger.warning(f"Could not initialize TabularFormatter: {e}")

    def _init_aggregator(self, aggregator):
        """Initialize aggregator in explicit mode only."""
        self.aggregator = None
        if aggregator and OperationAggregator:
            try:
                # Ensure aggregator is in explicit mode
                if hasattr(aggregator, "config") and hasattr(aggregator.config, "explicit_mode"):
                    aggregator.config.explicit_mode = True
                self.aggregator = aggregator
            except Exception as e:
                self.logger.warning(f"Could not initialize OperationAggregator: {e}")

    @property
    def _operation_stack(self) -> List[OperationContext]:
        """Thread-local operation stack."""
        if not hasattr(self._local, "operation_stack"):
            self._local.operation_stack = []
        return self._local.operation_stack

    @property
    def current_operation(self) -> Optional[OperationContext]:
        """Get current operation context."""
        return self._operation_stack[-1] if self._operation_stack else None

    def start_operation(self, operation_name: str, **context) -> str:
        """
        Start a new operation.

        Args:
            operation_name: Name of the operation to start
            **context: Additional context parameters

        Returns:
            operation_id: Unique identifier for this operation
        """
        # Check if operation should be filtered
        if self._should_filter_operation(operation_name):
            return ""  # Return empty ID for filtered operations

        operation_id = self._generate_operation_id(operation_name)
        parent_id = self.current_operation.operation_id if self.current_operation else None

        operation_context = OperationContext(
            operation_id=operation_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            parent_operation_id=parent_id,
        )

        # Add any additional context as metrics
        if context:
            operation_context.metrics.update(context)

        self._operation_stack.append(operation_context)

        # Log operation start
        self._log_operation_start(operation_context)

        # Integrate with operation_monitor if available (only for root operations)
        if self.operation_monitor and not parent_id:
            try:
                self.operation_monitor.start_operation_tracking(operation_name)
            except Exception as e:
                self.logger.warning(f"OperationMonitor integration error: {e}")

        # Integrate with aggregator if available (only for root operations)
        if self.aggregator and not parent_id:
            try:
                self.aggregator.start_operation(operation_name)
            except Exception as e:
                self.logger.warning(f"OperationAggregator integration error: {e}")

        return operation_id

    def end_operation(self, status: str = "SUCCESS", error_info: dict = None) -> None:
        """
        End the current operation and automatically generate ASCII table.

        Args:
            status: Operation completion status
            error_info: Optional error information dictionary
        """
        if not self._operation_stack:
            self.logger.warning("No active operation to end")
            return

        context = self._operation_stack.pop()
        context.end_time = datetime.now()
        context.status = status

        # Add error information if provided
        if error_info:
            context.error_info = error_info

        # Check if operation should be logged based on duration
        if not self._should_log_operation(context):
            return

        # Log operation end
        self._log_operation_end(context)

        # Update parent operation's sub-operation count
        if self.current_operation:
            self.current_operation.sub_operations_count += 1

        # Only handle aggregation and table generation for root operations
        if not context.parent_operation_id:
            self._handle_root_operation_end(context)

    def add_metric(self, key: str, value: Any) -> None:
        """
        Add a custom metric to the current operation with automatic data compression.

        Args:
            key: Metric name
            value: Metric value (automatically compressed if large)
        """
        if not self.current_operation:
            self.logger.warning(f"No active operation to add metric {key}")
            return

        # Apply data compression if enabled
        processed_value = self._compress_value(value) if self.compression_config.enabled else value
        self.current_operation.metrics[key] = processed_value  # Add metric to operation_monitor if available
        if (
            self.operation_monitor
            and hasattr(self.operation_monitor, "current_operation")
            and self.operation_monitor.current_operation
        ):
            try:
                self.operation_monitor.add_custom_metric(key, processed_value)
            except Exception as e:
                self.logger.debug(f"OperationMonitor metric integration error: {e}")

        # Log metric addition with compressed representation
        display_value = self._get_display_value(processed_value)
        self.logger.info(
            f"│ ├─ Метрика: {key} = {display_value}",
            extra={
                "operation_id": self.current_operation.operation_id,
                "metric_key": key,
                "metric_value": processed_value,
            },
        )

    def get_current_operation(self) -> Optional[OperationContext]:
        """Get the current operation context."""
        return self.current_operation

    def _handle_root_operation_end(self, context: OperationContext) -> None:
        """Handle completion of root operation with table generation and aggregator integration."""
        # Integrate with operation_monitor if available
        if self.operation_monitor:
            try:
                self.operation_monitor.end_operation_tracking()
            except Exception as e:
                self.logger.warning(f"OperationMonitor integration error: {e}")

        # Integrate with aggregator if available
        if self.aggregator:
            try:
                self.aggregator.end_operation()
            except Exception as e:
                self.logger.warning(f"OperationAggregator integration error: {e}")

        # Generate and display ASCII table if enabled
        if self.enable_tables and self.tabular_formatter:
            try:
                self._generate_operation_table(context)
            except Exception as e:
                self.logger.warning(f"Table generation error: {e}")

    def _generate_operation_table(self, context: OperationContext) -> None:
        """Generate ASCII table for completed operation."""
        if not self.tabular_formatter:
            return

        # Create table data structure
        table_data = self._create_operation_table_data(context)
        # Format and log the table
        if table_data and hasattr(self.tabular_formatter, "_format_ascii_table"):
            try:
                formatted_table = self.tabular_formatter._format_ascii_table(table_data)
                self.logger.info(f"\n{formatted_table}")
            except Exception as e:
                self.logger.debug(f"ASCII table formatting error: {e}")

    def _create_operation_table_data(self, context: OperationContext) -> Optional[Dict[str, Any]]:
        """Create table data structure for operation context."""
        try:
            # Prepare table data as a dictionary for TabularFormatter
            data_rows = [
                {"Metric": "Operation", "Value": context.operation_name},
                {"Metric": "Status", "Value": context.status},
                {"Metric": "Duration (s)", "Value": f"{context.duration:.3f}" if context.duration else "N/A"},
                {"Metric": "Sub-operations", "Value": str(context.sub_operations_count)},
                {"Metric": "Files Modified", "Value": str(context.files_modified)},
            ]

            # Add custom metrics
            for key, value in context.metrics.items():
                display_value = self._get_display_value(value)
                data_rows.append({"Metric": f"  {key}", "Value": display_value})

            # Add error information if present
            if context.error_info:
                data_rows.append({"Metric": "Error Type", "Value": context.error_info.get("type", "Unknown")})
                data_rows.append({"Metric": "Error Message", "Value": context.error_info.get("message", "Unknown")})

            # Create table data object
            status_emoji = "✅" if context.status == "SUCCESS" else "❌"
            title = f"{status_emoji} Operation Summary: {context.operation_name}"

            return {
                "title": title,
                "data": data_rows,
                "summary": f"Completed at {context.end_time.strftime('%H:%M:%S')}" if context.end_time else None,
                "table_type": "operation_summary",
            }

        except Exception as e:
            # Fallback to simple dict if there's any error
            self.logger.debug(f"Error creating table data: {e}")
            return {
                "title": f"Operation Summary: {context.operation_name}",
                "data": [
                    {"Metric": "Status", "Value": context.status},
                    {"Metric": "Duration", "Value": f"{context.duration:.3f}s" if context.duration else "N/A"},
                ],
                "table_type": "operation_summary",
            }

    def _compress_value(self, value: Any) -> Any:
        """
        Compress large data values using rules from former ValueAggregator.

        Args:
            value: Original value to potentially compress

        Returns:
            Compressed value or original if no compression needed
        """
        # Handle numpy arrays
        if HAS_NUMPY and isinstance(value, np.ndarray):
            return self._compress_numpy_array(value)

        # Handle pandas DataFrames
        if HAS_PANDAS and isinstance(value, pd.DataFrame):
            return self._compress_dataframe(value)

        # Handle large dictionaries
        if isinstance(value, dict) and len(value) >= self.compression_config.dict_threshold:
            return self._compress_dict(value)

        # Handle large lists
        if isinstance(value, list) and len(value) >= self.compression_config.array_threshold:
            return self._compress_list(value)

        # Handle long strings
        if isinstance(value, str) and len(value) >= self.compression_config.string_threshold:
            return self._compress_string(value)

        return value

    def _compress_numpy_array(self, array: "np.ndarray") -> Dict[str, Any]:  # type: ignore
        """Compress numpy array to summary."""
        if len(array) < self.compression_config.array_threshold:
            return array.tolist()

        return {
            "_compressed": True,
            "_type": "numpy.ndarray",
            "_shape": array.shape,
            "_dtype": str(array.dtype),
            "_length": len(array),
            "_preview": f"[{array[0]}, {array[1]}, ..., {array[-2]}, {array[-1]}]"
            if len(array) >= 4
            else str(array.tolist()),
            "_stats": {"min": float(array.min()), "max": float(array.max()), "mean": float(array.mean())}
            if array.dtype.kind in "biufc"
            else None,
        }

    def _compress_dataframe(self, df: "pd.DataFrame") -> Dict[str, Any]:  # type: ignore
        """Compress pandas DataFrame to summary."""
        if len(df) < self.compression_config.dataframe_threshold:
            return df.to_dict()

        return {
            "_compressed": True,
            "_type": "pandas.DataFrame",
            "_shape": df.shape,
            "_columns": list(df.columns),
            "_length": len(df),
            "_preview": f"DataFrame({df.shape[0]}×{df.shape[1]}) cols: {list(df.columns[:3])}"
            + ("..." if len(df.columns) > 3 else ""),
            "_head": df.head(3).to_dict() if len(df) > 3 else df.to_dict(),
            "_dtypes": df.dtypes.to_dict(),
        }

    def _compress_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress large dictionary to summary."""
        if len(data) < self.compression_config.dict_threshold:
            return data

        # Get first and last few items for preview
        items = list(data.items())
        preview_items = dict(items[:3] + items[-2:] if len(items) > 5 else items)

        return {
            "_compressed": True,
            "_type": "dict",
            "_length": len(data),
            "_keys": list(data.keys())[:10],  # First 10 keys
            "_preview": preview_items,
            "_full_keys_count": len(data),
        }

    def _compress_list(self, data: List[Any]) -> Dict[str, Any]:
        """Compress large list to summary."""
        if len(data) < self.compression_config.array_threshold:
            return data

        return {
            "_compressed": True,
            "_type": "list",
            "_length": len(data),
            "_preview": data[:3] + ["..."] + data[-2:] if len(data) > 5 else data,
            "_sample_types": list({type(item).__name__ for item in data[:10]}),
        }

    def _compress_string(self, data: str) -> Dict[str, Any]:
        """Compress long string to summary."""
        if len(data) < self.compression_config.string_threshold:
            return data

        return {
            "_compressed": True,
            "_type": "string",
            "_length": len(data),
            "_preview": f"{data[:100]}...{data[-50:]}" if len(data) > 150 else data,
            "_lines_count": data.count("\n") + 1,
        }

    def _get_display_value(self, value: Any) -> str:
        """Get display representation of value for logging."""
        if isinstance(value, dict) and value.get("_compressed"):
            type_name = value.get("_type", "unknown")
            length = value.get("_length", 0)
            value.get("_preview", "")

            if type_name == "numpy.ndarray":
                shape = value.get("_shape", ())
                return f"📊 {type_name}{shape} ({length} elements)"
            elif type_name == "pandas.DataFrame":
                shape = value.get("_shape", (0, 0))
                return f"📊 {type_name}({shape[0]}×{shape[1]})"
            elif type_name in ["dict", "list"]:
                return f"📊 {type_name}({length} items)"
            elif type_name == "string":
                return f"📊 string({length} chars)"

        # For regular values, try to make a reasonable display
        if isinstance(value, (list, tuple)) and len(value) > 10:
            return f"[{value[0]}, {value[1]}, ..., {value[-1]}] ({len(value)} items)"
        elif isinstance(value, dict) and len(value) > 5:
            first_key = next(iter(value))
            return f"{{{first_key}: ..., ...}} ({len(value)} items)"

        return str(value)

    def log_operation(self, operation_name: str):
        """
        Context manager for operation logging.

        Args:
            operation_name: Name of the operation

        Usage:
            with operation_logger.log_operation("LOAD_FILE"):
                # Your code here
                pass"""
        return _OperationContextManager(self, operation_name)

    def operation(self, name: Optional[str] = None):
        """
        Decorator for automatic operation logging with enhanced error handling.

        Args:
            name: Optional operation name (defaults to function name)

        Usage:
            @operation_logger.operation("CUSTOM_NAME")
            def my_function():
                pass
        """

        def decorator(func):
            operation_name = name or self._function_to_operation_name(func.__name__)

            @wraps(func)
            def wrapper(*args, **kwargs):
                # Use the enhanced context manager
                with self.log_operation(operation_name):
                    # Add function metadata as metrics
                    if hasattr(func, "__module__"):
                        self.add_metric("module", func.__module__)
                    if args and hasattr(args[0], "__class__"):
                        self.add_metric("class", args[0].__class__.__name__)

                    return func(*args, **kwargs)

            # Store operation metadata on the wrapper for introspection
            wrapper._operation_name = operation_name  # type: ignore
            wrapper._is_operation_decorated = True  # type: ignore
            wrapper._original_function = func  # type: ignore

            return wrapper

        return decorator

    def reset(self) -> None:
        """Reset the operation logger to clean state."""
        # Clear thread-local operation stack
        if hasattr(self._local, "operation_stack"):
            self._local.operation_stack.clear()

        # Reset the aggregator if present
        if self.aggregator and hasattr(self.aggregator, "reset"):
            try:
                self.aggregator.reset()
            except Exception as e:
                self.logger.warning(f"Error resetting aggregator: {e}")

        # Reset operation monitor if present
        if self.operation_monitor and hasattr(self.operation_monitor, "reset"):
            try:
                self.operation_monitor.reset()
            except Exception as e:
                self.logger.warning(f"Error resetting operation monitor: {e}")

    def register_error_handler(self, handler) -> None:
        """
        Register an error handler for operation error processing.

        Args:
            handler: OperationErrorHandler instance to register
        """
        if handler and handler not in self._error_handlers:
            self._error_handlers.append(handler)
            self.logger.debug(f"Registered error handler: {handler.get_handler_name()}")

    def unregister_error_handler(self, handler) -> None:
        """
        Unregister an error handler.

        Args:
            handler: OperationErrorHandler instance to unregister
        """
        if handler in self._error_handlers:
            self._error_handlers.remove(handler)
            self.logger.debug(f"Unregistered error handler: {handler.get_handler_name()}")

    def _handle_operation_error(self, error: Exception, operation_context: OperationContext) -> None:
        """
        Handle an error that occurred during operation through registered handlers.

        Args:
            error: The exception that occurred
            operation_context: Full context of the operation when error occurred
        """
        # Try each registered error handler
        for handler in self._error_handlers:
            try:
                result = handler.handle_operation_error(error, operation_context)
                if result and result.get("handled"):
                    self.logger.debug(f"Error handled by {handler.get_handler_name()}")

                    # Add error handling results to operation metrics
                    if operation_context.metrics is not None:
                        operation_context.metrics.update(
                            {
                                "error_handler": result.get("handler"),
                                "recovery_attempted": result.get("recovery_attempted", False),
                                "recovery_success": result.get("recovery_success", False),
                            }
                        )

                    # If recovery was successful, update operation status
                    if result.get("recovery_success"):
                        operation_context.status = "RECOVERED"
                        self.logger.info(f"✅ Operation {operation_context.operation_name} recovered from error")

                    break  # Stop after first successful handler

            except Exception as handler_error:
                # Log error in handler but continue with other handlers
                self.logger.warning(f"Error in error handler {handler.get_handler_name()}: {handler_error}")

        # Always use default handler as fallback
        if self._default_error_handler:
            try:
                self._default_error_handler.handle_operation_error(error, operation_context)
            except Exception as default_handler_error:
                self.logger.error(f"Error in default error handler: {default_handler_error}")

    def _generate_operation_id(self, operation_name: str) -> str:
        """Generate unique operation ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_part = secrets.token_hex(4)
        return f"{operation_name}_{timestamp}_{random_part}"

    def _function_to_operation_name(self, function_name: str) -> str:
        """Convert function name to operation name."""
        # Remove _handle_ prefix if present
        if function_name.startswith("_handle_"):
            function_name = function_name[8:]

        # Convert snake_case to UPPER_CASE
        return function_name.upper()

    def _log_operation_start(self, context: OperationContext) -> None:
        """Log operation start."""
        level_indicator = "│ " if context.parent_operation_id else ""
        self.logger.info(
            f"{level_indicator}🔄 OPERATION_START: {context.operation_name} (ID: {context.operation_id})",
            extra={
                "operation_id": context.operation_id,
                "operation_name": context.operation_name,
                "parent_operation_id": context.parent_operation_id,
                "operation_type": "start",
            },
        )

    def _log_operation_end(self, context: OperationContext) -> None:
        """Log operation end."""
        duration = context.duration
        level_indicator = "│ " if context.parent_operation_id else ""
        status_emoji = "✅" if context.status == "SUCCESS" else "❌"

        self.logger.info(
            f"{level_indicator}{status_emoji} OPERATION_END: {context.operation_name} "
            f"(Время: {duration:.3f}s, Статус: {context.status})",
            extra={
                "operation_id": context.operation_id,
                "operation_name": context.operation_name,
                "parent_operation_id": context.parent_operation_id,
                "operation_type": "end",
                "duration": duration,
                "status": context.status,
                "metrics": context.metrics,
            },
        )

    def _on_config_changed(self, section: str, key: str, value: Any) -> None:
        """Handle configuration changes."""
        try:
            if section == "tabular" and key == "enabled":
                self.enable_tables = value
                if value and not self.tabular_formatter and TabularFormatter:
                    self._initialize_tabular_formatter()
                elif not value:
                    self.tabular_formatter = None
            elif section == "logging" and key == "operation_timeout":
                # Update operation timeout if needed
                self._operation_timeout = value
            elif section == "logging" and key == "tabulate_format":
                # Reinitialize formatter with new format
                if self.tabular_formatter:
                    self._initialize_tabular_formatter()
        except Exception as e:
            self.logger.warning(f"Error applying configuration change {section}.{key}={value}: {e}")

    def _initialize_tabular_formatter(self) -> None:
        """Initialize or reinitialize tabular formatter with current config."""
        try:
            if self._tabular_config:
                format_style = self._tabular_config.format_style
            else:
                format_style = "grid"

            self.tabular_formatter = TabularFormatter(table_format=format_style)
        except Exception as e:
            self.logger.warning(f"Could not initialize TabularFormatter: {e}")

    def _should_filter_operation(self, operation_name: str) -> bool:
        """Check if operation should be filtered based on configuration."""
        if not self._operation_config:
            return False
        # Check exclude list
        if self._operation_config.exclude_operations and operation_name in self._operation_config.exclude_operations:
            return True

        # Check include-only list
        if (
            self._operation_config.include_only_operations
            and operation_name not in self._operation_config.include_only_operations
        ):
            return True

        return False

    def _should_log_operation(self, operation_context: OperationContext) -> bool:
        """Check if operation should be logged based on duration and configuration."""
        if not self._operation_config:
            return True

        duration = operation_context.duration or 0
        return duration >= self._operation_config.min_operation_duration

    # ...existing methods...


class _OperationContextManager:
    """Context manager for operation logging with enhanced error handling."""

    def __init__(self, operation_logger: OperationLogger, operation_name: str):
        self.operation_logger = operation_logger
        self.operation_name = operation_name
        self.operation_id = None

    def __enter__(self):
        self.operation_id = self.operation_logger.start_operation(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "ERROR" if exc_type is not None else "SUCCESS"
        error_info = None

        # Handle error through registered error handlers if exception occurred
        if exc_type is not None and exc_val is not None:
            # Get current operation context for error handlers
            current_context = self.operation_logger.get_current_operation()
            if current_context:
                # Call error handlers
                try:
                    self.operation_logger._handle_operation_error(exc_val, current_context)
                except Exception as handler_error:
                    # Log handler errors but don't fail the operation
                    self.operation_logger.logger.warning(f"Error handler failed: {handler_error}")

            # Collect exception details for operation end
            error_info = {
                "type": exc_type.__name__,
                "message": str(exc_val),
                "traceback": str(exc_tb) if exc_tb else None,
            }
            # Also add as metrics for compatibility
            self.operation_logger.add_metric("error_type", exc_type.__name__)
            self.operation_logger.add_metric("error_message", str(exc_val))

        self.operation_logger.end_operation(status, error_info)


# Global operation logger instance
# Delayed import to avoid circular dependency
_operation_logger = None


def get_operation_logger():
    """Get the global operation logger instance with operation_monitor integration."""
    global _operation_logger
    if _operation_logger is None:
        # Import here to avoid circular dependency
        from .operation_monitor import operation_monitor

        _operation_logger = OperationLogger(operation_monitor=operation_monitor)
    return _operation_logger


# For backward compatibility
operation_logger = get_operation_logger()


# Convenience functions for direct import
def log_operation(operation_name: str):
    """
    Convenience function for operation context manager.

    Usage:
        from src.log_aggregator.operation_logger import log_operation

        with log_operation("MY_OPERATION"):
            # Your code here
            pass
    """
    return operation_logger.log_operation(operation_name)


def operation(name: Optional[str] = None):
    """
    Convenience function for operation decorator.

    Usage:
        from src.log_aggregator.operation_logger import operation

        @operation("MY_OPERATION")
        def my_function():
            pass
    """
    return operation_logger.operation(name)
