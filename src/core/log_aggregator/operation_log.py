"""
Data structures for operation logging.

This module defines the core data structures used for operation tracking
and logging in the log aggregator module.
"""

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from .sub_operation_log import SubOperationLog

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from .meta_operation import MetaOperation


@dataclass
class OperationLog:
    """
    Data structure for storing operation execution information.

    This class captures all essential metrics for operation analysis:    - Basic operation identification and timing
    - Execution status and error handling
    - Sub-operation tracking through handle_request_cycle interception
    - Meta-operation clustering for improved readability
    """

    operation_name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "running"  # "success", "error", "running"
    execution_time: Optional[float] = None
    exception_info: Optional[str] = None
    sub_operations: List[SubOperationLog] = field(default_factory=list)
    meta_operations: List["MetaOperation"] = field(default_factory=list)
    # New fields for minimalist logging format
    source_module: Optional[str] = None  # Source module name (e.g., "calculations_data.py")
    source_line: Optional[int] = None  # Line number where operation was called
    caller_info: Optional[str] = None  # Additional caller context info

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

    @property
    def sub_operations_count(self) -> int:
        """Get the total number of sub-operations."""
        return len(self.sub_operations)

    @property
    def successful_sub_operations_count(self) -> int:
        """Get the number of successful sub-operations."""
        return sum(1 for sub_op in self.sub_operations if sub_op.status == "OK")

    @property
    def failed_sub_operations_count(self) -> int:
        """Get the number of failed sub-operations."""
        return sum(1 for sub_op in self.sub_operations if sub_op.status == "Error")

    @property
    def meta_operations_count(self) -> int:
        """Get the total number of meta-operations."""
        return len(self.meta_operations)

    @property
    def clustered_operations_count(self) -> int:
        """Get the number of sub-operations that are part of meta-operations."""
        return sum(len(meta_op.sub_operations) for meta_op in self.meta_operations)

    @property
    def standalone_operations_count(self) -> int:
        """Get the number of sub-operations that are not part of any meta-operation."""
        return self.sub_operations_count - self.clustered_operations_count

    def has_meta_operations(self) -> bool:
        """Check if this operation log contains any meta-operations."""
        return len(self.meta_operations) > 0
