"""
Operation Logger API for explicit operation boundaries marking.

This module provides a simple API for developers to explicitly mark operation
boundaries in code, enabling detailed tracking and analysis of user operations.
"""

import logging
import re
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

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

# Import OperationAggregator for integration
try:
    from .operation_aggregator import OperationAggregator
except ImportError:
    # Handle case where aggregator is not available
    OperationAggregator = None


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
    """Context information for a single operation."""

    operation_id: str
    operation_name: str
    start_time: datetime
    parent_operation_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "RUNNING"
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class OperationLogger:
    """
    Main API class for explicit operation logging with built-in data compression.

    Provides simple methods for marking operation boundaries and collecting
    custom metrics within operations. Includes functionality previously
    provided by ValueAggregator for large data handling.
    """

    def __init__(
        self,
        logger_name: str = "solid_state_kinetics.operations",
        aggregator=None,
        compression_config: Optional[DataCompressionConfig] = None,
    ):
        """
        Initialize the operation logger.

        Args:
            logger_name: Name of the logger to use for operation logging
            aggregator: Optional OperationAggregator for integration
            compression_config: Configuration for data compression
        """
        self.logger = logging.getLogger(logger_name)
        self.aggregator = aggregator
        self.compression_config = compression_config or DataCompressionConfig()
        self._local = threading.local()

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

    def start_operation(self, operation_name: str) -> str:
        """
        Start a new operation.

        Args:
            operation_name: Name of the operation to start

        Returns:
            operation_id: Unique identifier for this operation
        """
        operation_id = self._generate_operation_id(operation_name)
        parent_id = self.current_operation.operation_id if self.current_operation else None

        context = OperationContext(
            operation_id=operation_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            parent_operation_id=parent_id,
        )

        self._operation_stack.append(context)

        # Log operation start
        self._log_operation_start(context)

        # Integrate with aggregator if available
        if self.aggregator and not parent_id:  # Only start aggregation for root operations
            self.aggregator.start_operation(operation_name)

        return operation_id

    def end_operation(self, operation_id: Optional[str] = None, status: str = "SUCCESS") -> None:
        """
        End the current operation.

        Args:
            operation_id: Optional operation ID to end (defaults to current)
            status: Operation completion status
        """
        if not self._operation_stack:
            self.logger.warning("No active operation to end")
            return

        context = self._operation_stack.pop()

        # Validate operation ID if provided
        if operation_id and context.operation_id != operation_id:
            self.logger.warning(f"Operation ID mismatch: expected {context.operation_id}, got {operation_id}")

        context.end_time = datetime.now()
        context.status = status

        # Log operation end
        self._log_operation_end(context)

        # Integrate with aggregator if available
        if self.aggregator and not context.parent_operation_id:  # Only end aggregation for root operations
            self.aggregator.end_operation()

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
        self.current_operation.metrics[key] = processed_value  # Log metric addition with compressed representation
        display_value = self._get_display_value(processed_value)
        self.logger.info(
            f"│ ├─ Метрика: {key} = {display_value}",
            extra={
                "operation_id": self.current_operation.operation_id,
                "metric_key": key,
                "metric_value": processed_value,
            },
        )

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
                pass
        """
        return _OperationContextManager(self, operation_name)

    def operation(self, name: Optional[str] = None):
        """
        Decorator for automatic operation logging.

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
                with self.log_operation(operation_name):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def reset(self) -> None:
        """Reset the operation logger to clean state."""
        # Clear thread-local storage if it exists
        if hasattr(self._local, "current_operation"):
            self._local.current_operation = None

        # Reset the aggregator if present
        if self.aggregator and hasattr(self.aggregator, "reset"):
            self.aggregator.reset()

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


class _OperationContextManager:
    """Context manager for operation logging."""

    def __init__(self, operation_logger: OperationLogger, operation_name: str):
        self.operation_logger = operation_logger
        self.operation_name = operation_name
        self.operation_id = None

    def __enter__(self):
        self.operation_id = self.operation_logger.start_operation(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "ERROR" if exc_type is not None else "SUCCESS"

        # Log exception details if occurred
        if exc_type is not None:
            self.operation_logger.add_metric("error_type", exc_type.__name__)
            self.operation_logger.add_metric("error_message", str(exc_val))

        self.operation_logger.end_operation(self.operation_id, status)


# Global operation logger instance
operation_logger = OperationLogger()


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
