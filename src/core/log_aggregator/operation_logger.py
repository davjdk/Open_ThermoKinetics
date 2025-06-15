"""
Core operation logging functionality for MVP log aggregator.

This module implements the @operation decorator and related classes for capturing
and logging operation execution in the solid-state kinetics application.

Key components:
- OperationLog: Data structure for operation information
- @operation decorator: Wraps methods to capture execution metrics
- OperationLogger: Main logging orchestrator (future expansion)
"""

import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, TypeVar

from src.core.logger_config import LoggerManager

# Get logger for this module
logger = LoggerManager.get_logger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class OperationLog:
    """
    Data structure for storing operation execution information.

    This class captures all essential metrics for operation analysis:
    - Basic operation identification and timing
    - Execution status and error handling    - Placeholder for future sub-operation tracking
    """

    operation_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "running"  # "success", "error", "running"
    execution_time: Optional[float] = None
    exception_info: Optional[str] = None
    # Will be populated in Stage 2
    sub_operations: List[Any] = field(default_factory=list)

    def __post_init__(self):
        """Initialize operation with start timestamp."""
        if self.start_time is None:
            self.start_time = time.time()

    def mark_completed(self, success: bool = True, exception_info: Optional[str] = None) -> None:
        """
        Mark operation as completed with final status.

        Args:
            success: Whether operation completed successfully
            exception_info: Error information if operation failed
        """
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
        self.status = "success" if success else "error"
        if exception_info:
            self.exception_info = exception_info

    @property
    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds."""
        if self.execution_time is not None:
            return self.execution_time * 1000
        return None


class OperationLogger:
    """
    Main orchestrator for operation logging (placeholder for future expansion).

    This class will be extended in later stages to handle:
    - Sub-operation capture and aggregation
    - Table formatting with tabulate
    - Integration with LoggerManager
    - File output and rotation
    """

    def __init__(self):
        self.current_operation: Optional[OperationLog] = None

    def start_operation(self, operation_name: str) -> OperationLog:
        """Start tracking a new operation."""
        self.current_operation = OperationLog(operation_name=operation_name, start_time=time.time())
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

        logger.debug(
            f"Operation '{self.current_operation.operation_name}' completed "
            f"with status '{status}' in {duration:.2f}ms"
        )

        # In future stages, this is where we'll call table formatting and file output
        self.current_operation = None


def operation(operation_name: str) -> Callable[[F], F]:
    """
    Decorator for logging method execution as operations.

    This decorator wraps methods to capture:
    - Execution timing (start/end/duration)
    - Success/failure status
    - Exception information
    - Future: sub-operation tracking through handle_request_cycle

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
            operation_logger = OperationLogger()

            # Start operation tracking
            op_log = operation_logger.start_operation(operation_name)

            try:
                logger.info(f"Operation '{operation_name}' started at " f"{time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Execute the original method
                result = func(*args, **kwargs)

                # Mark successful completion
                operation_logger.complete_operation(success=True)
                logger.info(f"Operation '{operation_name}' completed successfully " f"in {op_log.duration_ms:.2f}ms")

                return result

            except Exception as e:
                # Capture exception information
                exception_info = f"{type(e).__name__}: {str(e)}"
                operation_logger.complete_operation(success=False, exception_info=exception_info)

                logger.error(
                    f"Operation '{operation_name}' failed after " f"{op_log.duration_ms:.2f}ms: {exception_info}"
                )

                # Re-raise the exception to preserve original behavior
                raise

        return wrapper

    return decorator
