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
    strategy_name: str = "unknown"  # Name of the clustering strategy used
    description: str = ""  # Human-readable description of the meta-operation
    sub_operations: List[SubOperationLog] = field(default_factory=list)
    start_time: Optional[float] = None  # Start timestamp
    end_time: Optional[float] = None  # End timestamp
    cluster_type: str = "unknown"  # Type of clustering used (temporal, semantic, etc.)
    cluster_parameters: dict = field(default_factory=dict)  # Parameters used for clustering
    # Специфические атрибуты для BaseSignalsBurst (Stage 3 implementation)
    real_actor: Optional[str] = None  # Реальный инициатор (main_window.py:446)
    burst_type: Optional[str] = None  # Тип бурста (Parameter_Update, Add_Reaction, etc.)
    target_distribution: Optional[dict] = None  # Распределение по targets
    temporal_characteristics: Optional[dict] = None  # Временные метрики

    @property
    def name(self) -> str:
        """Get the name/description for this meta-operation."""
        return self.description if self.description else self.strategy_name

    @property
    def execution_time(self) -> Optional[float]:
        """Get the total execution time of this meta-operation in seconds."""
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def duration_ms(self) -> float:
        """Get the total execution time in milliseconds."""
        if self.execution_time is not None:
            return self.execution_time * 1000
        # Fallback: sum of individual operation times
        return sum(op.execution_time for op in self.sub_operations if op.execution_time is not None)

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

    def get_targets_summary(self) -> str:
        """Get a summary of targets involved in this meta-operation."""
        targets = list({op.target for op in self.sub_operations})

        if len(targets) == 1:
            return targets[0]
        elif len(targets) <= 3:
            return ", ".join(targets)
        else:
            return f"{targets[0]}, ... (+{len(targets)-1})"

    def get_data_types_summary(self) -> str:
        """Get a summary of data types returned by operations in this group."""
        data_types = sorted({op.data_type for op in self.sub_operations})

        if len(data_types) == 1:
            return data_types[0]
        elif len(data_types) <= 3:
            return ", ".join(data_types)
        else:
            return "mixed"

    def get_status_summary(self) -> str:
        """Get a summary status for this meta-operation."""
        if self.failed_operations_count == 0:
            return "OK"
        elif self.successful_operations_count == 0:
            return "Error"
        else:
            return "Mixed"

    @property
    def total_execution_time(self) -> Optional[float]:
        """Get total execution time for all operations in the group."""
        # First try direct execution time
        if self.execution_time is not None:
            return self.execution_time

        # Fallback: calculate from sub-operations
        if not self.sub_operations:
            return None  # Sum execution times of sub-operations
        total = 0.0
        for op in self.sub_operations:
            if hasattr(op, "execution_time") and op.execution_time is not None:
                total += op.execution_time

        return total if total > 0 else None

    def __str__(self) -> str:
        """Return a clean string representation for logging."""
        return f"MetaOperation({self.meta_id}, {self.strategy_name}, {len(self.sub_operations)} ops)"

    def __repr__(self) -> str:
        """Return a detailed representation without response_data_raw."""
        sub_ops_summary = f"{len(self.sub_operations)} operations" if self.sub_operations else "no operations"
        return f"MetaOperation(meta_id='{self.meta_id}', " f"strategy='{self.strategy_name}', {sub_ops_summary})"

    # Stage 3: BaseSignals Burst Analysis Methods

    def is_base_signals_burst(self) -> bool:
        """Check if this meta-operation is a BaseSignals burst."""
        return self.strategy_name == "BaseSignalsBurst"

    def get_burst_performance_summary(self) -> str:
        """Get performance summary for BaseSignals bursts."""
        if not self.is_base_signals_burst() or not self.temporal_characteristics:
            return "N/A"

        ops_per_sec = self.temporal_characteristics.get("operations_per_second", 0)
        total_duration = self.temporal_characteristics.get("total_duration_ms", 0)

        if ops_per_sec > 100:
            return f"{ops_per_sec:.0f} ops/s, {total_duration:.1f}ms"
        else:
            return f"{total_duration:.1f}ms"

    def get_target_distribution_summary(self) -> str:
        """Get summary of target distribution for BaseSignals bursts."""
        if not self.target_distribution:
            return "unknown targets"

        if len(self.target_distribution) == 1:
            target = next(iter(self.target_distribution.keys()))
            count = self.target_distribution[target]
            return f"{target}({count})"
        else:
            targets_info = ", ".join([f"{target}({count})" for target, count in self.target_distribution.items()])
            return f"{len(self.target_distribution)} targets [{targets_info}]"

    def get_burst_type_description(self) -> str:
        """Get human-readable burst type description."""
        if not self.burst_type:
            return "Generic Signal Burst"

        burst_descriptions = {
            "Parameter_Update_Burst": "Parameter Update",
            "Add_Reaction_Burst": "Add Reaction",
            "Highlight_Reaction_Burst": "Highlight Reaction",
            "Multi_Target_Burst": "Multi-target Operation",
            "Generic_Signal_Burst": "Generic Signal",
        }

        return burst_descriptions.get(self.burst_type, self.burst_type.replace("_", " "))

    def get_enhanced_summary(self) -> str:
        """Get enhanced summary for BaseSignals bursts with all Stage 3 features."""
        if not self.is_base_signals_burst():
            return self.get_summary()

        burst_desc = self.get_burst_type_description()
        op_count = len(self.sub_operations)
        duration = self.temporal_characteristics.get("total_duration_ms", 0) if self.temporal_characteristics else 0

        base_summary = f"{burst_desc}: {op_count} operations in {duration:.1f}ms"

        # Add target information if multi-target
        if self.target_distribution and len(self.target_distribution) > 1:
            target_summary = self.get_target_distribution_summary()
            base_summary += f" across {target_summary}"

        # Add performance info for high-performance bursts
        perf_summary = self.get_burst_performance_summary()
        if "ops/s" in perf_summary:
            ops_per_sec = self.temporal_characteristics.get("operations_per_second", 0)
            base_summary += f" ({ops_per_sec:.0f} ops/s)"

        return base_summary

    def get_real_actor_info(self) -> str:
        """Get information about the real actor that initiated this burst."""
        if self.real_actor:
            return f"initiated by {self.real_actor}"
        return "actor unknown"
