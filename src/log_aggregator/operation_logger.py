"""
Operation Logger API for explicit operation boundaries marking.

This module provides a simple API for developers to explicitly mark operation
boundaries in code, enabling detailed tracking and analysis of user operations.
"""

import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

# Import OperationAggregator for integration
try:
    from .operation_aggregator import OperationAggregator
except ImportError:
    # Handle case where aggregator is not available
    OperationAggregator = None


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
    Main API class for explicit operation logging.

    Provides simple methods for marking operation boundaries and collecting
    custom metrics within operations.
    """

    def __init__(self, logger_name: str = "solid_state_kinetics.operations", aggregator=None):
        """
        Initialize the operation logger.

        Args:
            logger_name: Name of the logger to use for operation logging
            aggregator: Optional OperationAggregator for integration
        """
        self.logger = logging.getLogger(logger_name)
        self.aggregator = aggregator
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
        Add a custom metric to the current operation.

        Args:
            key: Metric name
            value: Metric value
        """
        if not self.current_operation:
            self.logger.warning(f"No active operation to add metric {key}")
            return

        self.current_operation.metrics[key] = value

        # Log metric addition
        self.logger.info(
            f"│ ├─ Метрика: {key} = {value}",
            extra={"operation_id": self.current_operation.operation_id, "metric_key": key, "metric_value": value},
        )

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
