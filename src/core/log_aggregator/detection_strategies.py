"""
Meta-operation detection strategies implementations.

This module contains concrete implementations of detection strategies
for identifying groups of related sub-operations.
"""

import re
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
            self.time_window_ms = float(kwargs["time_window_ms"])  # Reset cache when configuration changes
        self._cluster_cache.clear()
        self._cluster_counter = 0

    def _find_current_operation_index(
        self, sub_op: SubOperationLog, sorted_ops: List[SubOperationLog]
    ) -> Optional[int]:
        """Find the index of current operation in sorted list."""
        for i, op in enumerate(sorted_ops):
            if op == sub_op:
                return i
        return None

    def _find_cluster_boundaries(self, current_index: int, sorted_ops: List[SubOperationLog]) -> tuple:
        """Find cluster boundaries within time window."""
        current_time = sorted_ops[current_index].start_time
        time_window_seconds = self.time_window_ms / 1000.0

        cluster_start = current_index
        cluster_end = current_index

        # Look backwards within time window
        for i in range(current_index - 1, -1, -1):
            if current_time - sorted_ops[i].start_time <= time_window_seconds:
                cluster_start = i
            else:
                break

        # Look forwards within time window
        for i in range(current_index + 1, len(sorted_ops)):
            if sorted_ops[i].start_time - current_time <= time_window_seconds:
                cluster_end = i
            else:
                break

        return cluster_start, cluster_end

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a time-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a time cluster
        """
        if sub_op.start_time is None:
            return None

        # Sort operations by start time
        sorted_ops = sorted(
            [op for op in context.sub_operations if op.start_time is not None], key=lambda op: op.start_time
        )

        if not sorted_ops:
            return None

        # Find current operation in sorted list
        current_index = self._find_current_operation_index(sub_op, sorted_ops)
        if current_index is None:
            return None

        # Find cluster boundaries
        cluster_start, cluster_end = self._find_cluster_boundaries(current_index, sorted_ops)

        # Only create cluster if there are multiple operations
        if cluster_end > cluster_start:
            return f"time_window_{cluster_start}_{cluster_end}"

        return None


class NameSimilarityStrategy(MetaOperationStrategy):
    """
    Strategy for clustering operations with similar names.

    This strategy groups operations that have similar names based on:
    - Common prefixes (e.g., GET_*, SET_*, UPDATE_*)
    - Regular expression patterns
    - Configurable similarity rules
    """

    def __init__(self, name_pattern: str = "", prefix_length: int = 3, case_sensitive: bool = False):
        """
        Initialize strategy with name similarity parameters.

        Args:
            name_pattern: Regular expression pattern for grouping operation names
            prefix_length: Minimum length of common prefix for grouping
            case_sensitive: Whether to consider case when comparing names
        """
        self.name_pattern = name_pattern
        self.prefix_length = prefix_length
        self.case_sensitive = case_sensitive
        self._compiled_pattern = None
        self._prefix_groups: Dict[str, str] = {}

        if self.name_pattern:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._compiled_pattern = re.compile(self.name_pattern, flags)
            except re.error:
                # Invalid regex, fall back to prefix matching
                self._compiled_pattern = None

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "name_similarity"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "name_pattern" in kwargs:
            self.name_pattern = str(kwargs["name_pattern"])
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._compiled_pattern = re.compile(self.name_pattern, flags)
            except re.error:
                self._compiled_pattern = None

        if "prefix_length" in kwargs:
            self.prefix_length = int(kwargs["prefix_length"])

        if "case_sensitive" in kwargs:
            self.case_sensitive = bool(kwargs["case_sensitive"])

        # Reset cache when configuration changes
        self._prefix_groups.clear()

    def _get_operation_prefix(self, operation_name: str) -> str:
        """Extract prefix from operation name."""
        name = operation_name if self.case_sensitive else operation_name.lower()

        if "_" in name:
            return name.split("_")[0]
        elif len(name) >= self.prefix_length:
            return name[: self.prefix_length]
        else:
            return name

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a name-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a name cluster
        """
        operation_name = sub_op.operation_name
        if not self.case_sensitive:
            operation_name = operation_name.lower()  # First try regex pattern matching
        if self._compiled_pattern and self._compiled_pattern.search(operation_name):
            # Use a consistent cluster ID for all operations matching the pattern
            return "name_pattern_match"

        # Fall back to prefix matching
        prefix = self._get_operation_prefix(sub_op.operation_name)

        # Check if this prefix has been seen with other operations
        prefix_count = sum(
            1 for op in context.sub_operations if self._get_operation_prefix(op.operation_name) == prefix
        )

        # Only group if there are at least 2 operations with same prefix
        if prefix_count >= 2:
            return f"name_prefix_{prefix}"

        return None


class RequestParametersStrategy(MetaOperationStrategy):
    """
    Strategy for clustering operations with similar request parameters.

    This strategy groups operations that:
    - Have the same target
    - Share similar request_kwargs parameters
    - Meet configurable similarity thresholds
    """

    def __init__(
        self, target_grouping: bool = True, kwargs_similarity: float = 0.7, ignore_params: Optional[List[str]] = None
    ):
        """
        Initialize strategy with parameter similarity settings.

        Args:
            target_grouping: Whether to enable grouping by target
            kwargs_similarity: Similarity threshold for request parameters (0.0-1.0)
            ignore_params: List of parameter names to ignore when comparing
        """
        self.target_grouping = target_grouping
        self.kwargs_similarity = kwargs_similarity
        self.ignore_params = ignore_params or []
        self._parameter_groups: Dict[str, str] = {}

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "request_parameters"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "target_grouping" in kwargs:
            self.target_grouping = bool(kwargs["target_grouping"])

        if "kwargs_similarity" in kwargs:
            self.kwargs_similarity = float(kwargs["kwargs_similarity"])
            # Clamp to valid range
            self.kwargs_similarity = max(0.0, min(1.0, self.kwargs_similarity))

        if "ignore_params" in kwargs:
            self.ignore_params = list(kwargs["ignore_params"])

        # Reset cache when configuration changes
        self._parameter_groups.clear()

    def _calculate_params_similarity(self, params1: Dict, params2: Dict) -> float:
        """
        Calculate similarity between two parameter dictionaries.

        Args:
            params1: First parameter dictionary
            params2: Second parameter dictionary

        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        if not params1 and not params2:
            return 1.0

        if not params1 or not params2:
            return 0.0

        # Remove ignored parameters
        filtered_params1 = {k: v for k, v in params1.items() if k not in self.ignore_params}
        filtered_params2 = {k: v for k, v in params2.items() if k not in self.ignore_params}

        # Get all unique keys
        all_keys = set(filtered_params1.keys()) | set(filtered_params2.keys())
        if not all_keys:
            return 1.0

        # Count matching keys and values
        matches = sum(1 for key in all_keys if filtered_params1.get(key) == filtered_params2.get(key))

        return matches / len(all_keys)

    def _find_similar_operations(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """Find operations with similar parameters."""
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)
        current_params = getattr(sub_op, "request_kwargs", {}) or {}

        # Find current operation index
        current_index = next((i for i, op in enumerate(sorted_ops) if op == sub_op), None)

        if current_index is None:
            return None

        # Check parameter similarity with nearby operations
        for i, other_op in enumerate(sorted_ops):
            if i == current_index or abs(i - current_index) > 5:
                continue

            other_params = getattr(other_op, "request_kwargs", {}) or {}
            similarity = self._calculate_params_similarity(current_params, other_params)

            if similarity >= self.kwargs_similarity:
                min_index = min(current_index, i)
                return f"params_similar_{min_index}"

        return None

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a parameter-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a parameter cluster
        """
        # Check target grouping first
        if self.target_grouping:
            target_ops = [op for op in context.sub_operations if op.target == sub_op.target]
            if len(target_ops) >= 2:
                return f"target_params_{sub_op.target}"

        # Check parameter similarity
        return self._find_similar_operations(sub_op, context)


class SequenceCountStrategy(MetaOperationStrategy):
    """
    Strategy for clustering consecutive sequences of similar operations.

    This strategy identifies and groups sequences of N or more consecutive
    operations of the same type or with the same status.
    """

    def __init__(
        self,
        min_sequence: int = 3,
        operation_types: Optional[List[str]] = None,
        status_filter: Optional[List[str]] = None,
    ):
        """
        Initialize strategy with sequence parameters.

        Args:
            min_sequence: Minimum length of sequence to form a cluster
            operation_types: List of operation types to track for sequences
            status_filter: List of statuses to consider (OK, Error, Unknown)
        """
        self.min_sequence = min_sequence
        self.operation_types = operation_types or []
        self.status_filter = status_filter or ["OK", "Error"]
        self._sequence_groups: Dict[str, int] = {}

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "sequence_count"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "min_sequence" in kwargs:
            self.min_sequence = int(kwargs["min_sequence"])

        if "operation_types" in kwargs:
            self.operation_types = list(kwargs["operation_types"])

        if "status_filter" in kwargs:
            self.status_filter = list(kwargs["status_filter"])

        # Reset cache when configuration changes
        self._sequence_groups.clear()

    def _should_include_operation(self, sub_op: SubOperationLog) -> bool:
        """Check if operation should be included in sequence analysis."""
        if self.operation_types and sub_op.operation_name not in self.operation_types:
            return False

        if self.status_filter and sub_op.status not in self.status_filter:
            return False

        return True

    def _find_sequence_boundaries(self, sub_op: SubOperationLog, sorted_ops: List[SubOperationLog]) -> tuple:
        """Find the start and end of a sequence containing the given operation."""
        current_index = next((i for i, op in enumerate(sorted_ops) if op == sub_op), None)

        if current_index is None:
            return -1, -1

        operation_name = sub_op.operation_name
        status = sub_op.status

        # Find start of sequence
        sequence_start = current_index
        for i in range(current_index - 1, -1, -1):
            if sorted_ops[i].operation_name == operation_name and sorted_ops[i].status == status:
                sequence_start = i
            else:
                break

        # Find end of sequence
        sequence_end = current_index
        for i in range(current_index + 1, len(sorted_ops)):
            if sorted_ops[i].operation_name == operation_name and sorted_ops[i].status == status:
                sequence_end = i
            else:
                break

        return sequence_start, sequence_end

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a sequence-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a sequence cluster
        """
        if not self._should_include_operation(sub_op):
            return None

        # Sort operations by step number
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)

        # Find sequence boundaries
        sequence_start, sequence_end = self._find_sequence_boundaries(sub_op, sorted_ops)

        if sequence_start == -1:
            return None

        sequence_length = sequence_end - sequence_start + 1

        if sequence_length >= self.min_sequence:
            return f"sequence_{sub_op.operation_name}_{sub_op.status}_{sequence_start}_{sequence_length}"

        return None


class FrequencyThresholdStrategy(MetaOperationStrategy):
    """
    Strategy for clustering high-frequency operation bursts.

    This strategy identifies periods of high-frequency activity where
    the number of operations of a certain type exceeds a threshold
    within a time window.
    """

    def __init__(
        self, freq_threshold: int = 5, freq_window_ms: int = 1000, operation_whitelist: Optional[List[str]] = None
    ):
        """
        Initialize strategy with frequency parameters.

        Args:
            freq_threshold: Minimum number of operations to trigger clustering
            freq_window_ms: Time window in milliseconds for frequency analysis
            operation_whitelist: List of operation types to monitor for frequency
        """
        self.freq_threshold = freq_threshold
        self.freq_window_ms = freq_window_ms
        self.operation_whitelist = operation_whitelist or []
        self._frequency_clusters: Dict[str, str] = {}

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "frequency_threshold"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "freq_threshold" in kwargs:
            self.freq_threshold = int(kwargs["freq_threshold"])

        if "freq_window_ms" in kwargs:
            self.freq_window_ms = int(kwargs["freq_window_ms"])

        if "operation_whitelist" in kwargs:
            self.operation_whitelist = list(kwargs["operation_whitelist"])

        # Reset cache when configuration changes
        self._frequency_clusters.clear()

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a high-frequency cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a frequency cluster
        """
        # Filter by whitelist if configured
        if self.operation_whitelist and sub_op.operation_name not in self.operation_whitelist:
            return None

        if sub_op.start_time is None:
            return None

        # Sort operations by start time
        sorted_ops = sorted(
            [op for op in context.sub_operations if op.start_time is not None], key=lambda op: op.start_time
        )

        if not sorted_ops:
            return None

        # Find current operation in sorted list
        current_op = next((op for op in sorted_ops if op == sub_op), None)
        if current_op is None:
            return None

        current_time = current_op.start_time
        operation_name = current_op.operation_name
        window_start = current_time - (self.freq_window_ms / 1000.0)
        window_end = current_time + (self.freq_window_ms / 1000.0)

        # Count operations of same type within time window
        operations_in_window = [
            op
            for op in sorted_ops
            if (op.operation_name == operation_name and window_start <= op.start_time <= window_end)
        ]

        if len(operations_in_window) >= self.freq_threshold:
            # Create cluster ID based on operation type and time window
            window_id = f"{int(current_time * 1000) // self.freq_window_ms}"
            return f"freq_burst_{operation_name}_{window_id}"

        return None


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
        current_index = next((i for i, op in enumerate(sorted_ops) if op == sub_op), None)

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


class TargetClusterStrategy(MetaOperationStrategy):
    """
    Enhanced target-based clustering strategy with gap tolerance.

    This strategy groups operations with the same target, allowing for
    small gaps of different operations between them.
    """

    def __init__(
        self,
        target_list: Optional[List[str]] = None,
        max_gap: int = 1,
        strict_sequence: bool = False,
        min_cluster_size: int = 2,
    ):
        """
        Initialize strategy with target clustering parameters.

        Args:
            target_list: List of targets to consider for clustering
            max_gap: Maximum number of operations of different target allowed in sequence
            strict_sequence: Whether to require strict sequence without gaps
            min_cluster_size: Minimum number of operations to form a cluster
        """
        self.target_list = target_list or []
        self.max_gap = max_gap
        self.strict_sequence = strict_sequence
        self.min_cluster_size = min_cluster_size
        self._target_clusters: Dict[str, str] = {}

    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        return "target_cluster"

    def configure(self, **kwargs) -> None:
        """Configure strategy parameters."""
        if "target_list" in kwargs:
            self.target_list = list(kwargs["target_list"])

        if "max_gap" in kwargs:
            self.max_gap = int(kwargs["max_gap"])

        if "strict_sequence" in kwargs:
            self.strict_sequence = bool(kwargs["strict_sequence"])

        if "min_cluster_size" in kwargs:
            self.min_cluster_size = int(kwargs["min_cluster_size"])

        # Reset cache when configuration changes
        self._target_clusters.clear()

    def _find_cluster_boundaries_strict(
        self, sorted_ops: List[SubOperationLog], current_index: int, target: str
    ) -> tuple:
        """Find cluster boundaries with strict sequence (no gaps)."""
        cluster_start = current_index
        cluster_end = current_index

        # Look backwards
        for i in range(current_index - 1, -1, -1):
            if sorted_ops[i].target == target:
                cluster_start = i
            else:
                break

        # Look forwards
        for i in range(current_index + 1, len(sorted_ops)):
            if sorted_ops[i].target == target:
                cluster_end = i
            else:
                break

        return cluster_start, cluster_end

    def _find_cluster_boundaries_with_gaps(
        self, sorted_ops: List[SubOperationLog], current_index: int, target: str
    ) -> tuple:
        """Find cluster boundaries allowing gaps."""
        cluster_start = current_index
        cluster_end = current_index

        # Look backwards with gap tolerance
        gap_count = 0
        for i in range(current_index - 1, -1, -1):
            if sorted_ops[i].target == target:
                cluster_start = i
                gap_count = 0  # Reset gap counter
            elif gap_count < self.max_gap:
                gap_count += 1
            else:
                break  # Too many gaps, stop looking

        # Look forwards with gap tolerance
        gap_count = 0
        for i in range(current_index + 1, len(sorted_ops)):
            if sorted_ops[i].target == target:
                cluster_end = i
                gap_count = 0  # Reset gap counter
            elif gap_count < self.max_gap:
                gap_count += 1
            else:
                break  # Too many gaps, stop looking

        return cluster_start, cluster_end

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a target-based cluster with gap tolerance.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Cluster ID if operation belongs to a target cluster
        """
        # Filter by target list if configured
        if self.target_list and sub_op.target not in self.target_list:
            return None

        # Sort operations by step number
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)

        # Find current operation index
        current_index = next((i for i, op in enumerate(sorted_ops) if op == sub_op), None)

        if current_index is None:
            return None

        target = sub_op.target

        # Find cluster boundaries based on configuration
        if self.strict_sequence:
            cluster_start, cluster_end = self._find_cluster_boundaries_strict(sorted_ops, current_index, target)
        else:
            cluster_start, cluster_end = self._find_cluster_boundaries_with_gaps(sorted_ops, current_index, target)

        # Count actual target operations in range (excluding gap operations)
        target_ops_count = sum(1 for i in range(cluster_start, cluster_end + 1) if sorted_ops[i].target == target)

        if target_ops_count >= self.min_cluster_size:
            return f"target_cluster_{target}_{cluster_start}"

        return None
