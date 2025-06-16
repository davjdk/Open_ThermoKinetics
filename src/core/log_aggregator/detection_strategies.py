"""
Detection strategies for meta-operation clustering.

This module implements various strategies for detecting groups of related
sub-operations that can be clustered into meta-operations.
"""

from typing import Dict, List, Optional

from .meta_operation_detector import MetaOperationStrategy
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


class TimeWindowStrategy(MetaOperationStrategy):
    """
    Groups operations that occur within a specified time window.

    This strategy clusters sub-operations that execute close together in time,
    which often indicates they are part of the same logical workflow.
    """

    @property
    def strategy_name(self) -> str:
        return "TimeWindow"

    def validate_config(self) -> None:
        """Validate time window configuration."""
        required_params = ["window_ms"]
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"TimeWindowStrategy missing required parameter: {param}")

        if self.config["window_ms"] <= 0:
            raise ValueError("TimeWindowStrategy window_ms must be positive")

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a time-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if clustered, None otherwise
        """
        if not sub_op.start_time:
            return None

        window_ms = self.config["window_ms"] / 1000.0  # Convert to seconds
        # Find operations within time window
        current_time = sub_op.start_time
        cluster_ops = []

        for other_op in context.sub_operations:
            if other_op.start_time and abs(other_op.start_time - current_time) <= window_ms:
                cluster_ops.append(other_op)

        # Only cluster if we have multiple operations in window
        if len(cluster_ops) >= self.config.get("min_cluster_size", 2):
            # Create cluster ID based on earliest operation
            earliest_time = min(op.start_time for op in cluster_ops if op.start_time)
            return f"time_cluster_{int(earliest_time * 1000)}"

        return None

    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """Generate description for time-based cluster."""
        window_ms = self.config["window_ms"]
        return f"Time cluster ({window_ms}ms window): {len(operations)} operations"


class TargetClusterStrategy(MetaOperationStrategy):
    """
    Groups operations that target the same component.

    This strategy clusters sub-operations that interact with the same
    target component, indicating related functionality.

    Advanced features:
    - target_list: Only consider operations targeting specified components
    - max_gap: Maximum allowed gap between operations of same target
    - strict_sequence: Whether gaps should break clusters into separate ones
    - min_cluster_size: Minimum operations needed to form a cluster
    """

    @property
    def strategy_name(self) -> str:
        return "TargetCluster"

    def validate_config(self) -> None:
        """Validate target clustering configuration."""
        # Validate max_gap if provided
        if "max_gap" in self.config:
            max_gap = self.config["max_gap"]
            if not isinstance(max_gap, int) or max_gap < 0:
                raise ValueError("TargetClusterStrategy max_gap must be a non-negative integer")

        # Validate target_list if provided
        if "target_list" in self.config:
            target_list = self.config["target_list"]
            if not isinstance(target_list, list):
                raise ValueError("TargetClusterStrategy target_list must be a list")

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a target-based cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if clustered, None otherwise
        """
        if not sub_op.target:
            return None

        # Check if target is in whitelist (if specified)
        target_list = self.config.get("target_list")
        if target_list and sub_op.target not in target_list:
            return None

        # Find all operations with same target
        same_target_ops = [op for op in context.sub_operations if op.target == sub_op.target]

        min_cluster_size = self.config.get("min_cluster_size", 2)
        if len(same_target_ops) < min_cluster_size:
            return None

        # If advanced clustering is disabled, use simple approach
        max_gap = self.config.get("max_gap")
        strict_sequence = self.config.get("strict_sequence", False)

        if max_gap is None and not strict_sequence:
            # Simple clustering - all operations with same target
            return f"target_{sub_op.target}"  # Advanced clustering with gap analysis
        return self._detect_with_gap_analysis(sub_op, context, same_target_ops)

    def _detect_with_gap_analysis(
        self, sub_op: SubOperationLog, context: OperationLog, same_target_ops: List[SubOperationLog]
    ) -> Optional[str]:
        """Perform gap-aware clustering analysis."""
        max_gap = self.config.get("max_gap", float("inf"))
        strict_sequence = self.config.get("strict_sequence", False)
        min_cluster_size = self.config.get("min_cluster_size", 2)

        # Sort all operations by step number
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)

        # Find sequences of same-target operations within gap tolerance
        clusters = self._find_target_clusters(sorted_ops, sub_op.target, max_gap, strict_sequence)
        # Find which cluster contains our operation
        for cluster_id, cluster_ops in clusters.items():
            if len(cluster_ops) >= min_cluster_size and sub_op in cluster_ops:
                return cluster_id

        return None

    def _find_target_clusters(
        self, sorted_ops: List[SubOperationLog], target: str, max_gap: int, strict_sequence: bool
    ) -> Dict[str, List[SubOperationLog]]:
        """Find clusters of operations with same target, respecting gap rules."""
        clusters = {}
        cluster_counter = 1

        target_ops = [op for op in sorted_ops if op.target == target]
        if not target_ops:
            return clusters

        # Group operations into clusters based on gaps
        current_cluster = []
        current_cluster_id = f"target_{target}_{cluster_counter}"

        for i, op in enumerate(target_ops):
            if not current_cluster:
                # Start new cluster
                current_cluster = [op]
            else:
                # Check gap to previous operation in cluster
                prev_op = current_cluster[-1]

                # Find positions in sorted operations
                prev_pos = next(j for j, sorted_op in enumerate(sorted_ops) if sorted_op == prev_op)
                curr_pos = next(j for j, sorted_op in enumerate(sorted_ops) if sorted_op == op)

                gap = curr_pos - prev_pos - 1

                if strict_sequence and gap >= max_gap:
                    # Gap too large in strict mode - finalize current cluster and start new one
                    if len(current_cluster) >= 1:  # Save even single operations for now
                        clusters[current_cluster_id] = current_cluster

                    cluster_counter += 1
                    current_cluster_id = f"target_{target}_{cluster_counter}"
                    current_cluster = [op]
                elif not strict_sequence and gap > max_gap:
                    # Gap too large in non-strict mode - finalize current cluster and start new one
                    if len(current_cluster) >= 1:  # Save even single operations for now
                        clusters[current_cluster_id] = current_cluster

                    cluster_counter += 1
                    current_cluster_id = f"target_{target}_{cluster_counter}"
                    current_cluster = [op]
                else:
                    # Add to current cluster
                    current_cluster.append(op)  # Add final cluster
        if current_cluster:
            clusters[current_cluster_id] = current_cluster

        return clusters

    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """Generate description for target-based cluster."""
        if operations:
            target = operations[0].target
            return f"Target cluster ({target}): {len(operations)} operations"
        return f"Target cluster: {len(operations)} operations"


class NameSimilarityStrategy(MetaOperationStrategy):
    """
    Groups operations with similar names.

    This strategy clusters sub-operations that have similar operation names,
    which often indicates they are variants of the same operation type.
    """

    @property
    def strategy_name(self) -> str:
        return "NameSimilarity"

    def validate_config(self) -> None:
        """Validate name similarity configuration."""
        # No required parameters for this strategy
        pass

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a name-similarity cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if clustered, None otherwise
        """
        if not sub_op.operation_name:
            return None

        # Extract base operation name (remove prefixes/suffixes)
        base_name = self._extract_base_name(sub_op.operation_name)

        # Find operations with similar names
        similar_ops = []
        for op in context.sub_operations:
            if op.operation_name and self._are_names_similar(sub_op.operation_name, op.operation_name):
                similar_ops.append(op)

        min_cluster_size = self.config.get("min_cluster_size", 2)
        if len(similar_ops) >= min_cluster_size:
            return f"name_{base_name}"

        return None

    def _extract_base_name(self, operation_name: str) -> str:
        """Extract base name from operation name."""
        # Simple heuristic: take first part before underscore or use full name
        parts = operation_name.split("_")
        return parts[0] if parts else operation_name

    def _are_names_similar(self, name1: str, name2: str) -> bool:
        """Check if two operation names are similar."""
        # Simple similarity: same base name or one contains the other
        base1 = self._extract_base_name(name1)
        base2 = self._extract_base_name(name2)

        return base1 == base2 or base1 in name2 or base2 in name1

    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """Generate description for name-similarity cluster."""
        if operations:
            base_name = self._extract_base_name(operations[0].operation_name or "")
            return f"Name cluster ({base_name}): {len(operations)} operations"
        return f"Name cluster: {len(operations)} operations"


class SequenceCountStrategy(MetaOperationStrategy):
    """
    Groups operations that appear in sequences (same operation repeated).

    This strategy clusters sub-operations that represent the same operation
    executed multiple times in sequence, which often indicates batch processing.
    """

    @property
    def strategy_name(self) -> str:
        return "SequenceCount"

    def validate_config(self) -> None:
        """Validate sequence count configuration."""
        required_params = ["min_sequence_length"]
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"SequenceCountStrategy missing required parameter: {param}")

        if self.config["min_sequence_length"] < 2:
            raise ValueError("SequenceCountStrategy min_sequence_length must be >= 2")

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a sequence cluster.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if clustered, None otherwise
        """
        if not sub_op.operation_name:
            return None

        # Find consecutive operations with same name
        sequence_ops = self._find_sequence(sub_op, context)

        min_length = self.config["min_sequence_length"]
        if len(sequence_ops) >= min_length:
            # Use step number of first operation in sequence as cluster ID
            first_step = min(op.step_number for op in sequence_ops)
            return f"sequence_{sub_op.operation_name}_{first_step}"

        return None

    def _find_sequence(self, sub_op: SubOperationLog, context: OperationLog) -> List[SubOperationLog]:
        """Find consecutive operations with same name."""
        # Sort operations by step number
        sorted_ops = sorted(context.sub_operations, key=lambda op: op.step_number)

        # Find the position of current operation
        current_idx = None
        for i, op in enumerate(sorted_ops):
            if op.step_number == sub_op.step_number:
                current_idx = i
                break

        if current_idx is None:
            return [sub_op]

        # Find sequence of same operations
        sequence = [sub_op]
        operation_name = sub_op.operation_name

        # Look backwards
        for i in range(current_idx - 1, -1, -1):
            if sorted_ops[i].operation_name == operation_name:
                sequence.insert(0, sorted_ops[i])
            else:
                break

        # Look forwards
        for i in range(current_idx + 1, len(sorted_ops)):
            if sorted_ops[i].operation_name == operation_name:
                sequence.append(sorted_ops[i])
            else:
                break

        return sequence

    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """Generate description for sequence cluster."""
        if operations:
            op_name = operations[0].operation_name or "unknown"
            return f"Sequence cluster ({op_name}): {len(operations)} operations"
        return f"Sequence cluster: {len(operations)} operations"
