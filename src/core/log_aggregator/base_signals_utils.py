"""
Utility functions for BaseSignals burst analysis (Stage 3 implementation).

This module implements the detailed logic from STAGE_03_META_OPERATION_STRUCTURE.md:
- Context-Aware Actor Resolution
- Burst type determination
- Temporal characteristics calculation
- Target distribution analysis
- Enhanced summary generation
"""

from typing import Dict, List, Optional

from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


def extract_real_actor(context: Optional[OperationLog]) -> str:
    """
    Extract real actor from operation context.

    Args:
        context: Current operation log for context extraction

    Returns:
        str: Real actor or fallback to base_signals.py:51
    """
    if context and hasattr(context, "caller_info") and context.caller_info:
        filename = context.caller_info.filename
        line_number = context.caller_info.line_number
        return f"{filename}:{line_number}"
    return "base_signals.py:51"  # Fallback


def determine_burst_type(operations: List[SubOperationLog]) -> str:
    """
    Determine burst type based on operation patterns.

    Args:
        operations: List of sub-operations in the burst

    Returns:
        str: Burst type classification
    """
    if not operations:
        return "Generic_Signal_Burst"

    operation_types = [op.operation_name for op in operations]
    operation_names = [
        str(op_type).split(".")[-1] if hasattr(op_type, "name") else str(op_type) for op_type in operation_types
    ]  # Highlight pattern: GET_DF_DATA → GET_VALUE → HIGHLIGHT_* (check before multi-target)
    if any("GET_DF_DATA" in name for name in operation_names):
        if any("HIGHLIGHT" in name for name in operation_names):
            return "Highlight_Reaction_Burst"

    # Multi-target pattern: operations across multiple targets (check after specific patterns)
    targets = {op.target for op in operations}
    if len(targets) > 1:
        return "Multi_Target_Burst"

    # Parameter Update pattern: GET_VALUE → CHECK → SET_VALUE → UPDATE_VALUE
    if any("UPDATE_VALUE" in name for name in operation_names):
        if any("GET_VALUE" in name for name in operation_names):
            return "Parameter_Update_Burst"

    # Add Reaction pattern: SET_VALUE → GET_VALUE → UPDATE_VALUE (multiple)
    set_count = sum(1 for name in operation_names if "SET_VALUE" in name)
    if set_count >= 2 and any("UPDATE_VALUE" in name for name in operation_names):
        return "Add_Reaction_Burst"

    # Generic burst
    return "Generic_Signal_Burst"


def calculate_temporal_characteristics(operations: List[SubOperationLog]) -> Dict[str, float]:
    """
    Calculate temporal characteristics of a burst.

    Args:
        operations: List of sub-operations to analyze

    Returns:
        Dict containing temporal metrics
    """
    if not operations:
        return {}

    # Sort by start time for temporal analysis
    sorted_ops = sorted(operations, key=lambda op: op.start_time)

    # Basic metrics
    start_time = sorted_ops[0].start_time
    end_time = max(op.start_time + (op.execution_time or 0) for op in sorted_ops)
    total_duration = (end_time - start_time) * 1000  # Convert to milliseconds

    # Average operation duration
    avg_op_duration = sum(op.execution_time or 0 for op in operations) / len(operations) * 1000

    # Calculate gaps between operations
    gaps = []
    for i in range(1, len(sorted_ops)):
        gap = (sorted_ops[i].start_time - sorted_ops[i - 1].start_time) * 1000
        gaps.append(gap)

    max_gap = max(gaps) if gaps else 0.0

    # Operations per second
    ops_per_second = len(operations) / (total_duration / 1000) if total_duration > 0 else 0

    return {
        "total_duration_ms": total_duration,
        "avg_operation_duration_ms": avg_op_duration,
        "max_gap_ms": max_gap,
        "operations_per_second": ops_per_second,
        "operation_count": len(operations),
    }


def calculate_target_distribution(operations: List[SubOperationLog]) -> Dict[str, int]:
    """
    Calculate distribution of operations by target.

    Args:
        operations: List of sub-operations to analyze

    Returns:
        Dict mapping target names to operation counts
    """
    distribution = {}
    for op in operations:
        target = op.target
        distribution[target] = distribution.get(target, 0) + 1
    return distribution


def generate_burst_summary(
    operations: List[SubOperationLog], burst_type: str, temporal_chars: Dict[str, float], target_dist: Dict[str, int]
) -> str:
    """
    Generate informative summary for BaseSignals burst.

    Args:
        operations: List of operations in the burst
        burst_type: Classified burst type
        temporal_chars: Temporal characteristics
        target_dist: Target distribution

    Returns:
        str: Human-readable burst summary
    """
    op_count = len(operations)
    duration_ms = temporal_chars.get("total_duration_ms", 0)

    # Create human-readable burst type
    burst_descriptions = {
        "Parameter_Update_Burst": "Parameter Update Burst",
        "Add_Reaction_Burst": "Add Reaction Burst",
        "Highlight_Reaction_Burst": "Highlight Reaction Burst",
        "Multi_Target_Burst": "Multi-target Burst",
        "Generic_Signal_Burst": "BaseSignals Burst",
    }

    burst_desc = burst_descriptions.get(burst_type, burst_type.replace("_", " "))

    # Base summary
    base_summary = f"{burst_desc}: {op_count} operations in {duration_ms:.1f}ms"

    # Add target information for multi-target bursts
    if len(target_dist) > 1:
        targets_info = ", ".join([f"{target}({count})" for target, count in target_dist.items()])
        base_summary += f" across {len(target_dist)} targets [{targets_info}]"

    # Add performance information for high-performance bursts
    ops_per_sec = temporal_chars.get("operations_per_second", 0)
    if ops_per_sec > 100:
        base_summary += f" ({ops_per_sec:.0f} ops/s)"

    return base_summary


def generate_stable_meta_id(operations: List[SubOperationLog], cluster_index: int = 0) -> str:
    """
    Generate stable meta-operation ID.

    Args:
        operations: List of operations in the cluster
        cluster_index: Index of this cluster within the detection session

    Returns:
        str: Stable meta-operation identifier
    """
    if not operations:
        return f"base_signals_burst_empty_{cluster_index}"

    # Use timestamp of first operation + cluster index
    first_op = min(operations, key=lambda op: op.start_time)
    timestamp_ms = int(first_op.start_time * 1000)

    return f"base_signals_burst_{timestamp_ms}_{cluster_index}"


def is_base_signals_operation(sub_op: SubOperationLog, max_duration_ms: float = 10.0) -> bool:
    """
    Check if operation qualifies as a BaseSignals operation.

    Args:
        sub_op: Sub-operation to check
        max_duration_ms: Maximum duration for atomic operations

    Returns:
        bool: True if operation qualifies as BaseSignals burst candidate
    """
    # Check caller info for base_signals.py:51
    if not hasattr(sub_op, "caller_info") or not sub_op.caller_info:
        return False

    return (
        sub_op.caller_info.filename == "base_signals.py"
        and sub_op.caller_info.line_number == 51
        and len(sub_op.sub_operations) == 0  # Atomic operations
        and sub_op.duration_ms <= max_duration_ms
    )


def analyze_operation_patterns(operations: List[SubOperationLog]) -> Dict[str, any]:
    """
    Comprehensive analysis of operation patterns for burst classification.

    Args:
        operations: List of operations to analyze

    Returns:
        Dict containing pattern analysis results
    """
    if not operations:
        return {"pattern_type": "empty", "confidence": 0.0}
    # Extract operation names for pattern analysis
    operation_names = []
    for op in operations:
        if hasattr(op.operation_name, "name"):
            operation_names.append(op.operation_name.name)
        else:
            name_str = str(op.operation_name)
            if "." in name_str:
                operation_names.append(name_str.split(".")[-1])
            else:
                operation_names.append(name_str)
    # Analyze patterns
    patterns = {
        "crud_operations": sum(
            1 for name in operation_names if any(crud in name for crud in ["GET_", "SET_", "UPDATE_", "DELETE_"])
        ),
        "data_operations": sum(
            1
            for name in operation_names
            if any(data_op in name for data_op in ["LOAD_", "SAVE_", "EXPORT_", "IMPORT_"])
        ),
        "ui_operations": sum(
            1
            for name in operation_names
            if any(ui_op in name for ui_op in ["HIGHLIGHT_", "DISPLAY_", "SHOW_", "HIDE_"])
        ),
        "calculation_operations": sum(
            1 for name in operation_names if any(calc_op in name for calc_op in ["CALCULATE_", "COMPUTE_", "PROCESS_"])
        ),
    }

    # Determine dominant pattern
    max_pattern = max(patterns.items(), key=lambda x: x[1])
    total_ops = len(operations)
    confidence = max_pattern[1] / total_ops if total_ops > 0 else 0.0

    return {
        "pattern_type": max_pattern[0],
        "confidence": confidence,
        "pattern_counts": patterns,
        "total_operations": total_ops,
    }
