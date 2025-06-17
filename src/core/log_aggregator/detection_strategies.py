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


class BaseSignalsBurstStrategy(MetaOperationStrategy):
    """
    Groups BaseSignals operations that occur in bursts with intermediate noise operations.

    This strategy detects clusters of operations where:
    1. Multiple operations target or originate from the base_signals dispatcher
    2. Operations occur within a specified time window
    3. Intermediate operations between base_signals operations are treated as "noise"

    Based on analysis of base_signals.py structure:
    - Operations with target="base_signals" (direct dispatcher operations)
    - Operations where actor contains "base_signals" (dispatcher-initiated operations)
    """

    @property
    def strategy_name(self) -> str:
        return "BaseSignalsBurst"

    def validate_config(self) -> None:
        """Расширенная валидация конфигурации стратегии."""
        # Базовые обязательные параметры
        required_params = ["window_ms", "min_cluster_size"]
        for param in required_params:
            if param not in self.config:
                raise ValueError(f"BaseSignalsBurstStrategy missing required parameter: {param}")

        # Валидация типов и диапазонов
        window_ms = self.config["window_ms"]
        if not isinstance(window_ms, (int, float)) or window_ms <= 0:
            raise ValueError("BaseSignalsBurstStrategy window_ms must be positive number")

        min_cluster_size = self.config["min_cluster_size"]
        if not isinstance(min_cluster_size, int) or min_cluster_size < 1:
            raise ValueError("BaseSignalsBurstStrategy min_cluster_size must be integer >= 1")

        # Валидация опциональных параметров
        if "max_cluster_duration_ms" in self.config:
            max_duration = self.config["max_cluster_duration_ms"]
            if not isinstance(max_duration, (int, float)) or max_duration <= 0:
                raise ValueError("BaseSignalsBurstStrategy max_cluster_duration_ms must be positive")

            # Логическая проверка: максимальная длительность должна быть больше окна
            if max_duration < window_ms:
                raise ValueError("max_cluster_duration_ms must be >= window_ms")

        if "include_noise" in self.config:
            if not isinstance(self.config["include_noise"], bool):
                raise ValueError("BaseSignalsBurstStrategy include_noise must be boolean")

    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if operation belongs to a BaseSignals burst cluster.

        Logic:
        1. Check if sub_op is a base_signals operation
        2. Find all nearby base_signals operations in time window
        3. Include intermediate operations as noise
        4. Generate meta_id for cluster

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if clustered, None otherwise
        """
        if not self._is_base_signals_operation(sub_op):
            return None

        # Check if already clustered to prevent duplicates
        if self._is_already_clustered(sub_op, context):
            return None

        # Find base_signals operations in time window
        window_seconds = self.config["window_ms"] / 1000.0
        cluster_operations = self._find_time_window_cluster(sub_op, context, window_seconds)

        # Check minimum cluster size
        min_size = self.config.get("min_cluster_size", 2)
        base_signals_count = sum(1 for op in cluster_operations if self._is_base_signals_operation(op))

        if base_signals_count < min_size:
            return None

        # Generate unique cluster ID
        return self._generate_cluster_id(cluster_operations[0] if cluster_operations else sub_op)

    def _is_base_signals_operation(self, sub_op: SubOperationLog) -> bool:
        """
        Check if operation belongs to base_signals module.

        Analyzes target and operation_name fields to determine affiliation.

        Args:
            sub_op: Sub-operation to analyze

        Returns:
            bool: True if operation belongs to base_signals
        """
        # Direct check by target
        if sub_op.target == "base_signals":
            return True

        # Check by operation name (may contain basic signal operations)
        operation_lower = sub_op.operation_name.lower() if sub_op.operation_name else ""
        if "signal" in operation_lower or "request" in operation_lower:
            return True

        # Check by target (may be compound name)
        target_lower = str(sub_op.target).lower() if sub_op.target else ""
        if "base_signals" in target_lower or "signals" in target_lower:
            return True

        return False

    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """
        Generate human-readable description of BaseSignalsBurst cluster.

        Format: "BaseSignalsBurst: {count} операций, {duration} мс, actor: {actor}, шум: {noise_status}"

        Args:
            meta_id: The meta-operation identifier
            operations: List of operations in the cluster

        Returns:
            str: Human-readable description of the cluster
        """
        if not operations:
            return "BaseSignalsBurst: 0 операций"

        # Basic metrics
        count = len(operations)
        duration_ms = self._calculate_duration_ms(operations)

        # Analyze actors
        actor_info = self._analyze_actors(operations)
        # Analyze noise operations
        noise_info = self._analyze_noise_operations(operations)

        # Form final description
        return f"BaseSignalsBurst: {count} операций, {duration_ms} мс, actor: {actor_info}, шум: {noise_info}"

    def _calculate_duration_ms(self, operations: List[SubOperationLog]) -> int:
        """
        Calculate total cluster duration in milliseconds.

        Args:
            operations: Cluster operations

        Returns:
            int: Duration in milliseconds
        """
        if not operations:
            return 0

        # Filter operations with valid time
        timed_operations = [op for op in operations if op.start_time is not None]
        if not timed_operations:
            return 0

        # Find time boundaries - simplified to reduce complexity
        start_times = []
        end_times = []

        for op in timed_operations:
            if op.start_time:
                start_times.append(op.start_time)

            # Calculate end time
            if op.end_time:
                end_times.append(op.end_time)
            elif op.start_time and op.execution_time:
                end_times.append(op.start_time + op.execution_time)
            elif op.start_time:
                end_times.append(op.start_time)  # Fallback

        if not start_times or not end_times:
            return 0

        cluster_start = min(start_times)
        cluster_end = max(end_times)

        duration_seconds = cluster_end - cluster_start
        return int(duration_seconds * 1000)  # Convert to ms

    def _analyze_actors(self, operations: List[SubOperationLog]) -> str:
        """
        Analyze actors in the cluster of operations.

        Extracts information about operation initiators from SubOperationLog.
        Since there's no direct actor field, analyze available data.

        Args:
            operations: Cluster operations

        Returns:
            str: Actor description ("не задан", specific name, or "множественные")
        """
        # Try to extract actor from request_kwargs (if saved)
        actors = set()

        for op in operations:
            if hasattr(op, "request_kwargs") and op.request_kwargs:
                # From base_signals.py we see that actor is passed in request
                if "actor" in op.request_kwargs:
                    actor = op.request_kwargs["actor"]
                    if actor:
                        actors.add(str(actor))

            # Additional analysis - try to extract from operation_name
            # if it contains patterns like "component_name_operation"
            if op.operation_name and "_" in op.operation_name:
                potential_actor = op.operation_name.split("_")[0]
                if potential_actor not in ["get", "set", "update", "load", "save"]:  # Exclude verbs
                    actors.add(potential_actor)

        # Form result
        if not actors:
            return "не задан"
        elif len(actors) == 1:
            return list(actors)[0]
        else:
            # Multiple actors - return first + count
            first_actor = sorted(actors)[0]
            return f"{first_actor} (+{len(actors)-1})"

    def _analyze_noise_operations(self, operations: List[SubOperationLog]) -> str:
        """
        Analyze presence of noise operations in cluster.

        Args:
            operations: Cluster operations

        Returns:
            str: Noise status ("нет", "есть", "есть (X ops)")
        """
        noise_count = 0
        noise_targets = set()

        for op in operations:
            if not self._is_base_signals_operation(op):
                noise_count += 1
                if op.target:
                    noise_targets.add(str(op.target))

        if noise_count == 0:
            return "нет"
        elif noise_count == 1:
            return "есть"
        else:
            # Detailed information for multiple noise
            targets_info = ""
            if len(noise_targets) <= 2:
                targets_info = f" ({', '.join(sorted(noise_targets))})"
            elif len(noise_targets) > 2:
                targets_list = sorted(noise_targets)
                targets_info = f" ({targets_list[0]}, {targets_list[1]}, +{len(noise_targets)-2})"

            return f"есть ({noise_count} ops{targets_info})"

    def _find_time_window_cluster(
        self, sub_op: SubOperationLog, context: OperationLog, window_seconds: float
    ) -> List[SubOperationLog]:
        """
        Find all operations in time window, including intermediate ones.

        Args:
            sub_op: Current base_signals operation
            context: Full operation log
            window_seconds: Time window size in seconds

        Returns:
            List[SubOperationLog]: Operations in cluster (base_signals + noise)
        """
        if not sub_op.start_time:
            return [sub_op]

        cluster_ops = []
        base_signals_times = []

        # Collect all base_signals operations in window
        for op in context.sub_operations:
            if not op.start_time:
                continue

            if self._is_base_signals_operation(op):
                time_diff = abs(op.start_time - sub_op.start_time)
                if time_diff <= window_seconds:
                    base_signals_times.append(op.start_time)
                    cluster_ops.append(op)

        # If found only one base_signals operation - not a cluster
        if len([op for op in cluster_ops if self._is_base_signals_operation(op)]) < 2:
            return []

        # Determine cluster time boundaries
        min_time = min(base_signals_times)
        max_time = max(base_signals_times)

        # Add intermediate operations (noise)
        if self.config.get("include_noise", True):
            noise_ops = self._collect_noise_operations(context, min_time, max_time)
            cluster_ops.extend(noise_ops)

        # Sort by execution time
        cluster_ops.sort(key=lambda x: x.start_time or 0)
        return cluster_ops

    def _collect_noise_operations(
        self, context: OperationLog, min_time: float, max_time: float
    ) -> List[SubOperationLog]:
        """
        Collect operations from other modules between base_signals operations.

        Args:
            context: Full operation log
            min_time: Start of cluster time interval
            max_time: End of cluster time interval

        Returns:
            List[SubOperationLog]: Intermediate operations (noise)
        """
        noise_operations = []

        for op in context.sub_operations:
            if not op.start_time:
                continue

            # Operation within cluster time boundaries
            if min_time <= op.start_time <= max_time:
                # But not a base_signals operation
                if not self._is_base_signals_operation(op):
                    noise_operations.append(op)

        return noise_operations

    def _generate_cluster_id(self, first_operation: SubOperationLog) -> str:
        """
        Generate unique identifier for cluster.

        Args:
            first_operation: First operation in cluster by time

        Returns:
            str: Unique cluster ID
        """
        # Use timestamp of first operation for uniqueness
        timestamp = int(first_operation.start_time * 1000) if first_operation.start_time else 0
        return f"base_signals_burst_{timestamp}_{first_operation.step_number}"

    def _is_already_clustered(self, sub_op: SubOperationLog, context: OperationLog) -> bool:
        """
        Check if operation was already included in another cluster.

        Prevents creation of overlapping clusters.
        """
        # Check existing meta-operations in context
        for meta_op in getattr(context, "meta_operations", []):
            if any(op.step_number == sub_op.step_number for op in meta_op.sub_operations):
                return True
        return False

    def _get_cluster_statistics(self, operations: List[SubOperationLog]) -> dict:
        """
        Collect detailed cluster statistics for debugging and extended analysis.

        Args:
            operations: Cluster operations

        Returns:
            Dict[str, Any]: Cluster statistics
        """
        base_signals_ops = [op for op in operations if self._is_base_signals_operation(op)]
        noise_ops = [op for op in operations if not self._is_base_signals_operation(op)]

        stats = {
            "total_operations": len(operations),
            "base_signals_operations": len(base_signals_ops),
            "noise_operations": len(noise_ops),
            "duration_ms": self._calculate_duration_ms(operations),
            "actors": self._get_all_actors(operations),
            "noise_targets": list({op.target for op in noise_ops if op.target}),
            "time_span": None,
        }

        # Add time span if available
        if any(op.start_time for op in operations):
            valid_times = [op.start_time for op in operations if op.start_time]
            if valid_times:
                stats["time_span"] = {
                    "start": min(valid_times),
                    "end": max(op.end_time or op.start_time for op in operations if op.start_time),
                }

        return stats

    def _get_all_actors(self, operations: List[SubOperationLog]) -> List[str]:
        """Extract all unique actors from operations."""
        actors = set()
        for op in operations:
            if hasattr(op, "request_kwargs") and op.request_kwargs:
                if "actor" in op.request_kwargs and op.request_kwargs["actor"]:
                    actors.add(str(op.request_kwargs["actor"]))
        return sorted(actors)

    def _handle_edge_cases(self, operations: List[SubOperationLog]) -> dict:
        """
        Handle special cases in cluster.

        Returns:
            Dict[str, str]: Dictionary with warnings or cluster peculiarities
        """
        warnings = {}

        # Check for operations without time
        no_time_ops = [op for op in operations if not op.start_time]
        if no_time_ops:
            warnings["timing"] = f"{len(no_time_ops)} операций без времени"

        # Check for operations with errors
        error_ops = [op for op in operations if op.status == "Error"]
        if error_ops:
            warnings["errors"] = f"{len(error_ops)} операций с ошибками"

        # Check for suspiciously long clusters (>1 second)
        duration_ms = self._calculate_duration_ms(operations)
        if duration_ms > 1000:
            warnings["duration"] = f"длинный кластер ({duration_ms}мс)"

        return warnings


# Export list for module
__all__ = [
    "TimeWindowStrategy",
    "NameSimilarityStrategy",
    "TargetClusterStrategy",
    "SequenceCountStrategy",
    "BaseSignalsBurstStrategy",  # НОВЫЙ ЭКСПОРТ
    "MetaOperationStrategy",
]
