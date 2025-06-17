"""
Meta-operation detection strategies and interfaces.

This module defines the abstract interfaces for meta-operation detection
strategies and the main detector class that coordinates multiple strategies.

Stage 3 enhancements: Enhanced MetaOperation creation with BaseSignals-specific
attributes including real actor resolution and comprehensive analytics.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .base_signals_utils import (
    calculate_target_distribution,
    calculate_temporal_characteristics,
    determine_burst_type,
    extract_real_actor,
)
from .meta_operation import MetaOperation
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


class MetaOperationStrategy(ABC):
    """
    Abstract base class for meta-operation detection strategies.

    Each strategy implements a specific heuristic for detecting
    groups of related sub-operations that can be clustered together.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy with configuration.

        Args:
            config: Strategy-specific configuration parameters
        """
        self.config = config
        self.logger = logging.getLogger(f"solid_state_kinetics.meta_operations.{self.strategy_name}")
        self.validate_config()

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the name of this detection strategy."""
        pass

    @abstractmethod
    def validate_config(self) -> None:
        """Validate strategy configuration parameters."""
        pass

    @abstractmethod
    def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
        """
        Detect if a sub-operation belongs to a meta-operation.

        Args:
            sub_op: The sub-operation to analyze
            context: The full operation log for context

        Returns:
            Optional[str]: Meta-operation ID if the operation belongs to a group,
                         None if it should remain standalone
        """
        pass

    @abstractmethod
    def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
        """
        Generate description for a meta-operation.

        Args:
            meta_id: The meta-operation identifier
            operations: List of operations in the meta-operation

        Returns:
            str: Human-readable description of the meta-operation
        """
        pass


class MetaOperationDetector:
    """
    Main detector class that coordinates multiple detection strategies.

    This class applies configured strategies to identify meta-operations
    and creates the appropriate MetaOperation objects according to the
    detailed logic defined in stage_04_detector_logic.md.
    """

    def __init__(
        self, strategies: Optional[List[MetaOperationStrategy]] = None, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize detector with strategies and configuration.

        Args:
            strategies: List of detection strategies to apply
            config: General detector configuration
        """
        self.strategies = strategies or []
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.logger = logging.getLogger("solid_state_kinetics.meta_operations.detector")

    def detect_meta_operations(self, operation_log: OperationLog) -> None:
        """
        Main algorithm for detecting meta-operations.

        Implements the detailed logic from stage_04_detector_logic.md:
        1. Check preconditions
        2. Analyze operations with strategies
        3. Assign operations to meta-groups
        4. Post-process and finalize meta-operations

        Args:
            operation_log: The operation log to analyze and modify in-place
        """
        # Step 1: Check preconditions
        if not self.enabled or not self.strategies or not operation_log.sub_operations:
            operation_log.meta_operations = []
            return  # Step 2: Create containers for detected groups
        meta_operations_dict: Dict[str, MetaOperation] = {}
        operation_assignments: Dict[int, str] = {}  # step_number -> meta_op_id

        # Step 3: Analyze operations with strategies
        self._analyze_operations_with_strategies(operation_log, meta_operations_dict, operation_assignments)

        # Step 4: Post-process and finalize meta-operations
        self._finalize_meta_operations(operation_log, meta_operations_dict)

    def _analyze_operations_with_strategies(
        self,
        operation_log: OperationLog,
        meta_operations_dict: Dict[str, MetaOperation],
        operation_assignments: Dict[int, str],
    ) -> None:
        """
        Apply strategies to operations for detecting groups.

        Args:
            operation_log: The operation log being analyzed
            meta_operations_dict: Dictionary to store detected meta-operations
            operation_assignments: Dictionary to track operation assignments
        """
        for sub_op in operation_log.sub_operations:
            # Check if operation was already assigned
            if sub_op.step_number in operation_assignments:
                continue  # Apply strategies in priority order
            for strategy in self.strategies:
                try:
                    meta_id = strategy.detect(sub_op, operation_log)
                    if meta_id is not None:
                        # Assign operation to meta-group
                        self._assign_operation_to_meta(
                            sub_op, meta_id, strategy, meta_operations_dict, operation_assignments
                        )
                        break  # Use first strategy that matches (priority order)

                except Exception as e:
                    self.logger.warning(
                        f"Error in strategy {strategy.strategy_name} for operation {sub_op.step_number}: {e}"
                    )
                    continue

    def _assign_operation_to_meta(
        self,
        sub_op: SubOperationLog,
        meta_id: str,
        strategy: MetaOperationStrategy,
        meta_operations_dict: Dict[str, MetaOperation],
        operation_assignments: Dict[int, str],
    ) -> None:
        """
        Assign operation to a meta-group.

        Args:
            sub_op: The sub-operation to assign
            meta_id: The meta-operation identifier
            strategy: The strategy that detected this group
            meta_operations_dict: Dictionary of meta-operations
            operation_assignments: Dictionary of operation assignments
        """
        # Create new meta-operation if needed
        if meta_id not in meta_operations_dict:
            # Create basic meta-operation
            meta_operations_dict[meta_id] = MetaOperation(
                meta_id=meta_id,
                strategy_name=strategy.strategy_name,
                description=strategy.get_meta_operation_description(meta_id, [sub_op]),
            )

        # Add operation to group
        meta_operations_dict[meta_id].sub_operations.append(sub_op)
        operation_assignments[sub_op.step_number] = meta_id

        # Debug logging
        if self.config.get("debug_mode", False):
            self.logger.debug(
                f"Operation {sub_op.step_number} ({sub_op.operation_name}) "
                f"assigned to meta-operation '{meta_id}' by {strategy.strategy_name}"
            )

    def _finalize_meta_operations(
        self, operation_log: OperationLog, meta_operations_dict: Dict[str, MetaOperation]
    ) -> None:
        """
        Finalize detected meta-operations with Stage 3 enhancements.

        Args:
            operation_log: The operation log to update
            meta_operations_dict: Dictionary of detected meta-operations
        """
        # Filter groups by minimum size
        valid_meta_operations = []
        min_group_size = self.config.get("min_group_size", 2)

        for meta_op in meta_operations_dict.values():
            if len(meta_op.sub_operations) >= min_group_size:
                # Sort operations by step_number
                meta_op.sub_operations.sort(key=lambda op: op.step_number)

                # Stage 3: Enhance BaseSignals meta-operations with additional attributes
                if meta_op.strategy_name == "BaseSignalsBurst":
                    self._enhance_base_signals_meta_operation(meta_op, operation_log)

                # Update description with final data
                meta_op.description = self._generate_final_description(meta_op)

                valid_meta_operations.append(meta_op)
            else:
                # Log filtered groups
                self.logger.debug(
                    f"Meta-operation '{meta_op.meta_id}' filtered out: "
                    f"size {len(meta_op.sub_operations)} < {min_group_size}"
                )

        # Sort meta-operations by start time
        valid_meta_operations.sort(key=lambda mo: mo.start_time or 0)

        # Add to operation_log
        operation_log.meta_operations = valid_meta_operations

        # Log detection statistics
        if self.config.get("debug_mode", False):
            self._log_detection_statistics(operation_log, meta_operations_dict)

    def _enhance_base_signals_meta_operation(self, meta_op: MetaOperation, context: OperationLog) -> None:
        """
        Enhance BaseSignals meta-operation with Stage 3 attributes.

        Args:
            meta_op: The BaseSignals meta-operation to enhance
            context: The operation context for real actor extraction
        """
        if not meta_op.sub_operations:
            return

        # Extract real actor from context
        meta_op.real_actor = extract_real_actor(context)

        # Determine burst type
        meta_op.burst_type = determine_burst_type(meta_op.sub_operations)

        # Calculate temporal characteristics
        meta_op.temporal_characteristics = calculate_temporal_characteristics(meta_op.sub_operations)

        # Calculate target distribution
        meta_op.target_distribution = calculate_target_distribution(meta_op.sub_operations)

        # Set start and end times from temporal characteristics
        if meta_op.temporal_characteristics and meta_op.sub_operations:
            first_op = min(meta_op.sub_operations, key=lambda op: op.start_time)
            last_op = max(meta_op.sub_operations, key=lambda op: op.start_time + (op.execution_time or 0))
            meta_op.start_time = first_op.start_time
            meta_op.end_time = last_op.start_time + (last_op.execution_time or 0)

    def _generate_final_description(self, meta_op: MetaOperation) -> str:
        """
        Generate final description for a meta-operation.

        Args:
            meta_op: The meta-operation to describe

        Returns:
            str: Final description
        """
        if not meta_op.sub_operations:
            return f"Meta-operation: {meta_op.meta_id}"

        # Stage 3: Use enhanced summary for BaseSignals meta-operations
        if meta_op.is_base_signals_burst():
            return meta_op.get_enhanced_summary()

        # Fallback to standard description for other types
        op_count = len(meta_op.sub_operations)
        strategy = meta_op.strategy_name
        duration = meta_op.duration_ms

        if duration is not None:
            try:
                return f"{strategy} cluster: {op_count} operations in {float(duration):.1f}ms"
            except (ValueError, TypeError):
                return f"{strategy} cluster: {op_count} operations (duration unknown)"
        else:
            return f"{strategy} cluster: {op_count} operations"

    def _log_detection_statistics(
        self, operation_log: OperationLog, all_meta_operations: Dict[str, MetaOperation]
    ) -> None:
        """
        Log detection statistics for debugging.

        Args:
            operation_log: The analyzed operation log
            all_meta_operations: All detected meta-operations before filtering
        """
        total_operations = len(operation_log.sub_operations)
        total_meta_operations = len(operation_log.meta_operations)
        grouped_operations = sum(len(mo.sub_operations) for mo in operation_log.meta_operations)
        ungrouped_operations = total_operations - grouped_operations

        # Statistics by strategy
        strategy_stats = {}
        for meta_op in operation_log.meta_operations:
            strategy = meta_op.strategy_name
            strategy_stats[strategy] = strategy_stats.get(strategy, 0) + 1

        self.logger.debug(
            f"Meta-operation detection complete:\n"
            f"  Total operations: {total_operations}\n"
            f"  Meta-operations created: {total_meta_operations}\n"
            f"  Operations grouped: {grouped_operations}\n"
            f"  Operations ungrouped: {ungrouped_operations}\n"
            f"  Strategy statistics: {strategy_stats}"
        )

    # Utility methods for external access
    def add_strategy(self, strategy: MetaOperationStrategy) -> None:
        """Add a detection strategy to the detector."""
        self.strategies.append(strategy)

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        Remove a strategy by name.

        Args:
            strategy_name: Name of the strategy to remove

        Returns:
            bool: True if strategy was found and removed, False otherwise
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.strategy_name == strategy_name:
                del self.strategies[i]
                return True
        return False

    def clear_strategies(self) -> None:
        """Remove all strategies from the detector."""
        self.strategies.clear()

    def get_strategy_names(self) -> List[str]:
        """Get names of all configured strategies."""
        return [strategy.strategy_name for strategy in self.strategies]

    def is_enabled(self) -> bool:
        """Check if detector has any enabled strategies."""
        return self.enabled and len(self.strategies) > 0

    def register_component(self, component_name: str) -> None:
        """Register component for logging purposes."""
        self.logger.info(f"Registered meta-operation detector component: {component_name}")
