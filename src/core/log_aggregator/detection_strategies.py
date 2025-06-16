"""
Meta-operation detection strategies implementations.

This module contains concrete implementations of detection strategies
for identifying groups of related sub-operations.
"""

from typing import Dict, List, Optional

from .meta_operation_detector import MetaOperationStrategy
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


class TimeWindowClusterStrategy(MetaOperationStrategy):
    """
    Strategy for clustering operations that start within a time window.

    This strategy groups operations that begin execution within a configurable
    time window, indicating they are likely part of the same logical operation.
    """

    def __init__(self, time_window_ms: float = 50.0):
        """
        Initialize strategy with time window parameter.

        Args:
            time_window_ms: Time window in milliseconds for clustering operations
        """
        self.time_window_ms = time_window_ms
        self._cluster_counter = 0
        self._cluster_cache: Dict[str, str] = {}  # Cache for operation groupings

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "time_window"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "time_window_ms" in kwargs:
            self.time_window_ms = float(kwargs["time_window_ms"])

        # Reset cache when configuration changes
        self._cluster_cache.clear()
        self._cluster_counter = 0

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a time-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a time cluster
        """
        # Find operations that started within the time window
        time_window_sec = self.time_window_ms / 1000.0

        for other_op in context.sub_operations:
            if other_op == sub_op:
                continue

            time_diff = abs(sub_op.start_time - other_op.start_time)

            if time_diff <= time_window_sec:
                # Check if other operation already has a cluster ID
                other_op_key = f"{other_op.step_number}_{other_op.start_time}"
                if other_op_key in self._cluster_cache:
                    cluster_id = self._cluster_cache[other_op_key]
                    # Add current operation to the same cluster
                    current_op_key = f"{sub_op.step_number}_{sub_op.start_time}"
                    self._cluster_cache[current_op_key] = cluster_id
                    return cluster_id

        # No existing cluster found, check if we should create a new one
        nearby_ops = [
            op
            for op in context.sub_operations
            if op != sub_op and abs(op.start_time - sub_op.start_time) <= time_window_sec
        ]

        if nearby_ops:
            # Create new cluster
            self._cluster_counter += 1
            cluster_id = f"time_window_{self._cluster_counter}"

            # Cache all operations in this cluster
            current_op_key = f"{sub_op.step_number}_{sub_op.start_time}"
            self._cluster_cache[current_op_key] = cluster_id

            for op in nearby_ops:
                op_key = f"{op.step_number}_{op.start_time}"
                if op_key not in self._cluster_cache:
                    self._cluster_cache[op_key] = cluster_id

            return cluster_id

        return None


class NameSimilarityStrategy(MetaOperationStrategy):
    """
    Strategy for clustering operations with similar names.

    This strategy groups operations that share common prefixes or patterns
    in their operation names, indicating they perform similar functions.
    """

    def __init__(self, prefix_min_length: int = 3, min_group_size: int = 2):
        """
        Initialize strategy with similarity parameters.

        Args:
            prefix_min_length: Minimum length of shared prefix to consider
            min_group_size: Minimum number of operations to form a group
        """
        self.prefix_min_length = prefix_min_length
        self.min_group_size = min_group_size
        self._name_groups: Dict[str, List[SubOperationLog]] = {}
        self._processed_operations: set = set()

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "name_similarity"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "prefix_min_length" in kwargs:
            self.prefix_min_length = int(kwargs["prefix_min_length"])
        if "min_group_size" in kwargs:
            self.min_group_size = int(kwargs["min_group_size"])

        # Reset cache when configuration changes
        self._name_groups.clear()
        self._processed_operations.clear()

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a name-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a name cluster
        """
        op_key = f"{sub_op.step_number}_{sub_op.operation_name}"

        # Skip if already processed
        if op_key in self._processed_operations:
            return None

        # Find operations with similar names
        similar_ops = []
        op_name = sub_op.operation_name

        for other_op in context.sub_operations:
            if other_op == sub_op:
                continue

            # Check for common prefix
            common_prefix = self._get_common_prefix(op_name, other_op.operation_name)
            if len(common_prefix) >= self.prefix_min_length:
                similar_ops.append(other_op)

        if len(similar_ops) >= (self.min_group_size - 1):  # -1 because we don't count current op
            # Create or find existing group
            group_key = op_name[: self.prefix_min_length]

            if group_key not in self._name_groups:
                self._name_groups[group_key] = []

            # Add current operation and similar operations to group
            self._name_groups[group_key].append(sub_op)
            self._name_groups[group_key].extend(similar_ops)

            # Mark all operations as processed
            self._processed_operations.add(op_key)
            for op in similar_ops:
                other_key = f"{op.step_number}_{op.operation_name}"
                self._processed_operations.add(other_key)

            return f"name_similarity_{group_key}"

        return None

    def _get_common_prefix(self, str1: str, str2: str) -> str:
        """Get the common prefix of two strings."""
        i = 0
        min_len = min(len(str1), len(str2))

        while i < min_len and str1[i] == str2[i]:
            i += 1

        return str1[:i]


class TargetSimilarityStrategy(MetaOperationStrategy):
    """
    Strategy for clustering operations with the same target.

    This strategy groups consecutive operations that target the same
    system component (same 'target' field).
    """

    def __init__(self, min_sequence_length: int = 2):
        """
        Initialize strategy with sequence parameters.

        Args:
            min_sequence_length: Minimum number of consecutive operations to form a group
        """
        self.min_sequence_length = min_sequence_length
        self._target_sequences: Dict[str, int] = {}

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "target_similarity"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "min_sequence_length" in kwargs:
            self.min_sequence_length = int(kwargs["min_sequence_length"])

        # Reset cache when configuration changes
        self._target_sequences.clear()

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a target-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a target cluster
        """
        # Sort operations by step number to analyze sequences
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)

        # Find the position of current operation
        current_index = None
        for i, op in enumerate(sorted_ops):
            if op == sub_op:
                current_index = i
                break

        if current_index is None:
            return None

        target = sub_op.target

        # Look for consecutive operations with the same target
        sequence_start = current_index
        sequence_end = current_index

        # Look backwards
        for i in range(current_index - 1, -1, -1):
            if sorted_ops[i].target == target:
                sequence_start = i
            else:
                break

        # Look forwards
        for i in range(current_index + 1, len(sorted_ops)):
            if sorted_ops[i].target == target:
                sequence_end = i
            else:
                break

        sequence_length = sequence_end - sequence_start + 1

        if sequence_length >= self.min_sequence_length:
            # Create cluster ID based on target and sequence position
            return f"target_similarity_{target}_{sequence_start}"

        return None
