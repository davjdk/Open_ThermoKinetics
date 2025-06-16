"""
Meta-operation data structures for clustering sub-operations.

This module defines data structures for representing meta-operations -
logical groups of related sub-operations that can be clustered together
for improved log readability and analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .sub_operation_log import SubOperationLog


@dataclass
class MetaOperation:
    """
    Data structure for representing a logical group of related sub-operations.

    Meta-operations are created by clustering algorithms that detect patterns
    in sub-operation sequences such as temporal proximity, similar names,
    or common targets.
    """

    meta_id: str  # Unique identifier for this meta-operation
    name: str  # Human-readable name/description
    heuristic: str  # Name of the detection strategy that created this group
    sub_operations: List[SubOperationLog] = field(default_factory=list)
    start_time: Optional[float] = None  # Start time of first operation in group
    end_time: Optional[float] = None  # End time of last operation in group
    execution_time: Optional[float] = None  # Total execution time of the group

    def __post_init__(self):
        """Calculate timing information from sub-operations."""
        if self.sub_operations:
            self.start_time = min(sub_op.start_time for sub_op in self.sub_operations)

            # Calculate end time from operations that have completed
            completed_ops = [sub_op for sub_op in self.sub_operations if sub_op.end_time is not None]
            if completed_ops:
                self.end_time = max(sub_op.end_time for sub_op in completed_ops)
                if self.start_time is not None and self.end_time is not None:
                    self.execution_time = self.end_time - self.start_time

    @property
    def duration_ms(self) -> Optional[float]:
        """Get execution duration in milliseconds."""
        if self.execution_time is not None:
            return self.execution_time * 1000
        return None

    @property
    def operations_count(self) -> int:
        """Get the total number of operations in this meta-operation."""
        return len(self.sub_operations)

    @property
    def successful_operations_count(self) -> int:
        """Get the number of successful operations in this meta-operation."""
        return sum(1 for sub_op in self.sub_operations if sub_op.status == "OK")

    @property
    def failed_operations_count(self) -> int:
        """Get the number of failed operations in this meta-operation."""
        return sum(1 for sub_op in self.sub_operations if sub_op.status == "Error")

    @property
    def success_rate(self) -> float:
        """Get the success rate of operations in this meta-operation."""
        if self.operations_count == 0:
            return 0.0
        return self.successful_operations_count / self.operations_count

    def get_summary(self) -> str:
        """Get a brief summary of this meta-operation."""
        return (
            f"{self.name}: {self.operations_count} ops, "
            f"{self.successful_operations_count} successful, "
            f"{self.duration_ms:.1f}ms"
        )
