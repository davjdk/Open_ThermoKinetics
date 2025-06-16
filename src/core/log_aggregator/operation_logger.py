"""
Core operation logging functionality for MVP log aggregator.

This module implements the @operation decorator and related classes for capturing
and logging operation execution in the solid-state kinetics application.

Key components:
- OperationLog: Data structure for operation information
- @operation decorator: Wraps methods to capture execution metrics
- OperationLogger: Main logging orchestrator with sub-operation capture
- HandleRequestCycleProxy: Proxy for intercepting handle_request_cycle calls
"""

import functools
import inspect
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from ..logger_config import LoggerManager
from .aggregated_operation_logger import get_aggregated_logger
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog
from .table_formatter import format_operation_log

# Get logger for this module
logger = LoggerManager.get_logger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Thread-local storage for tracking current operation context
_operation_context = threading.local()


def get_current_operation_logger() -> Optional["OperationLogger"]:
    """Get the current operation logger from thread-local storage."""
    return getattr(_operation_context, "current_logger", None)


def set_current_operation_logger(operation_logger: Optional["OperationLogger"]) -> None:
    """Set the current operation logger in thread-local storage."""
    _operation_context.current_logger = operation_logger


class HandleRequestCycleProxy:
    """
    Proxy class for intercepting handle_request_cycle calls during operations.

    This proxy wraps the original handle_request_cycle method to capture
    sub-operation information while preserving the original behavior.
    """

    def __init__(self, original_method: Callable, instance: Any):
        """
        Initialize the proxy with the original method and instance.

        Args:
            original_method: The original handle_request_cycle method
            instance: The instance that owns the method
        """
        self.original_method = original_method
        self.instance = instance

    def __call__(self, target: str, operation: str, **kwargs) -> Any:
        """
        Proxy call that captures sub-operation data and calls original method.

        Args:
            target: The target system for the request
            operation: The operation to be performed
            **kwargs: Additional parameters for the request

        Returns:
            Any: The response from the original method
        """
        operation_logger = get_current_operation_logger()
        if operation_logger is None:
            # No active operation, just call original method
            return self.original_method(target, operation, **kwargs)

        # Create sub-operation log entry
        step_number = len(operation_logger.current_operation.sub_operations) + 1
        sub_op_log = SubOperationLog(
            step_number=step_number,
            operation_name=operation,
            target=target,
            start_time=time.time(),
            request_kwargs=kwargs.copy(),
        )

        # Add to current operation tracking
        operation_logger.current_operation.sub_operations.append(sub_op_log)

        try:
            # Call the original method
            response = self.original_method(target, operation, **kwargs)

            # Mark sub-operation as completed successfully
            sub_op_log.mark_completed(response_data=response)

            logger.debug(
                f"Sub-operation {step_number}: {operation} -> {target} "
                f"completed in {sub_op_log.duration_ms:.2f}ms with status {sub_op_log.status}"
            )

            return response

        except Exception as e:
            # Mark sub-operation as failed
            exception_info = f"{type(e).__name__}: {str(e)}"
            sub_op_log.mark_completed(response_data=None, exception_info=exception_info)

            logger.debug(
                f"Sub-operation {step_number}: {operation} -> {target} "
                f"failed after {sub_op_log.duration_ms:.2f}ms: {exception_info}"
            )

            # Re-raise the exception to preserve original behavior
            raise


class OperationLogger:
    """
    Main orchestrator for operation logging with sub-operation capture.

    This class manages the complete lifecycle of operation tracking:
    - Starting and completing operations
    - Setting up handle_request_cycle interception
    - Collecting and managing sub-operation data
    - Preparing data for table formatting (future stages)
    """

    def __init__(self):
        self.current_operation: Optional[OperationLog] = None
        self._original_methods: dict = {}  # Store original methods for restoration

    def _capture_caller_info(self, operation_log: OperationLog) -> None:
        """
        Capture information about the calling code location.

        Args:
            operation_log: The operation log to populate with caller info
        """
        frame = inspect.currentframe()
        try:
            # Navigate up the call stack to find the decorated function
            # Stack: _capture_caller_info -> start_operation -> wrapper -> decorated_function
            for _ in range(4):  # Move up 4 frames to reach the decorated function
                frame = frame.f_back
                if frame is None:
                    break

            if frame:
                filename = frame.f_code.co_filename
                line_number = frame.f_lineno
                module_name = Path(filename).name
                function_name = frame.f_code.co_name

                operation_log.source_module = module_name
                operation_log.source_line = line_number
                operation_log.caller_info = f"{module_name}:{line_number} in {function_name}()"

                logger.debug(f"Captured caller info: {operation_log.caller_info}")

        except Exception as e:
            # Graceful fallback - should not interrupt main operation
            operation_log.source_module = "unknown"
            operation_log.source_line = 0
            operation_log.caller_info = f"capture_failed: {str(e)}"
            logger.debug(f"Failed to capture caller info: {e}")
        finally:
            del frame

    def start_operation(self, operation_name: str) -> OperationLog:
        """Start tracking a new operation."""
        self.current_operation = OperationLog(operation_name=operation_name, start_time=time.time())

        # Capture caller information for minimalist logging format
        self._capture_caller_info(self.current_operation)

        logger.debug(f"Operation '{operation_name}' started")
        return self.current_operation

    def complete_operation(self, success: bool = True, exception_info: Optional[str] = None) -> None:
        """Complete the current operation tracking."""
        if self.current_operation is None:
            logger.warning("Attempting to complete operation, but no operation is active")
            return

        self.current_operation.mark_completed(success=success, exception_info=exception_info)
        duration = self.current_operation.duration_ms
        status = self.current_operation.status
        sub_op_count = self.current_operation.sub_operations_count
        successful_count = self.current_operation.successful_sub_operations_count
        failed_count = self.current_operation.failed_sub_operations_count

        logger.debug(
            f"Operation '{self.current_operation.operation_name}' completed "
            f"with status '{status}' in {duration:.2f}ms. "
            f"Sub-operations: {sub_op_count} total, {successful_count} successful, {failed_count} failed"
        )  # Log to aggregated operations file using the new AggregatedOperationLogger
        try:
            aggregated_logger = get_aggregated_logger()
            aggregated_logger.log_operation(self.current_operation)
        except Exception as e:
            logger.error(f"Failed to write aggregated operation log: {e}")
            # Fallback to old behavior for debugging
            try:
                formatted_log = format_operation_log(self.current_operation)
                logger.info(f"Aggregated operation log:\n{formatted_log}")
            except Exception as e2:
                logger.error(f"Failed to format operation log: {e2}")

        self.current_operation = None

    def setup_handle_request_cycle_interception(self, instance: Any) -> None:
        """
        Set up interception of handle_request_cycle method for the given instance.

        Args:
            instance: The object instance that has handle_request_cycle method
        """
        if not hasattr(instance, "handle_request_cycle"):
            logger.warning(f"Instance {instance} does not have handle_request_cycle method")
            return

        # Store original method for restoration
        original_method = instance.handle_request_cycle
        instance_id = id(instance)
        self._original_methods[instance_id] = original_method

        # Create and set proxy
        proxy = HandleRequestCycleProxy(original_method, instance)
        instance.handle_request_cycle = proxy

        logger.debug(f"Set up handle_request_cycle interception for {instance}")

    def restore_handle_request_cycle(self, instance: Any) -> None:
        """
        Restore the original handle_request_cycle method for the given instance.

        Args:
            instance: The object instance to restore
        """
        instance_id = id(instance)
        if instance_id in self._original_methods:
            instance.handle_request_cycle = self._original_methods[instance_id]
            del self._original_methods[instance_id]
            logger.debug(f"Restored original handle_request_cycle for {instance}")
        else:
            logger.warning(f"No original method stored for instance {instance}")

    def get_sub_operations_summary(self) -> dict:
        """
        Get a summary of sub-operations for the current operation.

        Returns:
            dict: Summary information about sub-operations
        """
        if self.current_operation is None:
            return {}

        return {
            "total_count": self.current_operation.sub_operations_count,
            "successful_count": self.current_operation.successful_sub_operations_count,
            "failed_count": self.current_operation.failed_sub_operations_count,
            "sub_operations": [sub_op.to_dict() for sub_op in self.current_operation.sub_operations],
        }


def operation(operation_name: str) -> Callable[[F], F]:
    """
    Decorator for logging method execution as operations.

    This decorator wraps methods to capture:
    - Execution timing (start/end/duration)
    - Success/failure status
    - Exception information
    - Sub-operation tracking through handle_request_cycle interception

    Args:
        operation_name: Human-readable name for the operation

    Returns:
        Decorated function with logging capabilities

    Example:
        @operation("DATA_PROCESSING")
        def process_experimental_data(self, file_path: str) -> bool:
            # Method implementation
            return True
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Initialize operation logger instance
            operation_logger = OperationLogger()  # Start operation tracking
            op_log = operation_logger.start_operation(operation_name)

            # Set current operation logger in thread-local storage
            set_current_operation_logger(operation_logger)

            # Set up handle_request_cycle interception if instance has the method
            instance = None
            if args and hasattr(args[0], "handle_request_cycle"):
                instance = args[0]
                operation_logger.setup_handle_request_cycle_interception(instance)

            try:
                logger.info(f"Operation '{operation_name}' started at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Execute the original method
                result = func(*args, **kwargs)

                # Get summary before completing operation
                sub_ops_summary = operation_logger.get_sub_operations_summary()

                # Mark successful completion
                operation_logger.complete_operation(success=True)
                duration = op_log.duration_ms or 0.0

                logger.info(
                    f"Operation '{operation_name}' completed successfully "
                    f"in {duration:.2f}ms with {sub_ops_summary.get('total_count', 0)} sub-operations"
                )

                return result

            except Exception as e:
                # Get summary before completing operation
                sub_ops_summary = operation_logger.get_sub_operations_summary()

                # Capture exception information
                exception_info = f"{type(e).__name__}: {str(e)}"
                operation_logger.complete_operation(success=False, exception_info=exception_info)
                duration = op_log.duration_ms or 0.0

                logger.error(
                    f"Operation '{operation_name}' failed after "
                    f"{duration:.2f}ms with {sub_ops_summary.get('total_count', 0)} sub-operations: {exception_info}"
                )

                # Re-raise the exception to preserve original behavior
                raise

            finally:
                # Restore original handle_request_cycle method if it was intercepted
                if instance is not None:
                    operation_logger.restore_handle_request_cycle(instance)

                # Clear current operation logger from thread-local storage
                set_current_operation_logger(None)

        return wrapper

    return decorator
