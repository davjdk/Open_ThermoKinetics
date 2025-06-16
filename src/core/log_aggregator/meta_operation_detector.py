"""
Meta-operation detection strategies and interfaces.

This module defines the abstract interfaces for meta-operation detection
strategies and the main detector class that coordinates multiple strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .meta_operation import MetaOperation
from .operation_log import OperationLog
from .sub_operation_log import SubOperationLog


class MetaOperationStrategy(ABC):
    """
    Abstract base class for meta-operation detection strategies.

    Each strategy implements a specific heuristic for detecting
    groups of related sub-operations that can be clustered together.
    """

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this detection strategy."""
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
    def configure(self, **kwargs) -> None:
        """
        Configure strategy parameters.

        Args:
            **kwargs: Strategy-specific configuration parameters
        """
        pass


class MetaOperationDetector:
    """
    Main detector class that coordinates multiple detection strategies.

    This class applies configured strategies to identify meta-operations
    and creates the appropriate MetaOperation objects.
    """

    def __init__(self, strategies: Optional[List[MetaOperationStrategy]] = None):
        """
        Initialize detector with a list of strategies.

        Args:
            strategies: List of detection strategies to apply
        """
        self.strategies = strategies or []
        self._meta_operation_counter = 0

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
            if strategy.get_strategy_name() == strategy_name:
                del self.strategies[i]
                return True
        return False

    def clear_strategies(self) -> None:
        """Remove all strategies from the detector."""
        self.strategies.clear()

    def detect_meta_operations(self, operation_log: OperationLog) -> None:
        """
        Detect and create meta-operations within the given operation log.

        This method modifies the operation_log in-place by adding a
        meta_operations attribute containing detected MetaOperation objects.

        Args:
            operation_log: The operation log to analyze
        """
        if not self.strategies or not operation_log.sub_operations:
            # No strategies configured or no operations to analyze
            operation_log.meta_operations = []
            return

        # Dictionary to collect operations by meta-operation ID
        meta_groups: Dict[str, List[SubOperationLog]] = {}
        # Apply each strategy to each sub-operation
        for sub_op in operation_log.sub_operations:
            for strategy in self.strategies:
                try:
                    meta_id = strategy.detect(sub_op, operation_log)
                    if meta_id is not None:
                        # Found a meta-operation match
                        if meta_id not in meta_groups:
                            meta_groups[meta_id] = []
                        meta_groups[meta_id].append(sub_op)
                        # Use first strategy that matches (priority order)
                        break
                except Exception:
                    # Log error but continue with other strategies
                    # This ensures detection errors don't break the logging system
                    pass

        # Create MetaOperation objects from grouped operations
        meta_operations = []
        for meta_id, sub_ops in meta_groups.items():
            if len(sub_ops) > 1:  # Only create meta-operations for groups of 2+
                # Extract strategy name from meta_id (assuming format "strategy_name_id")
                strategy_name = meta_id.split("_")[0] if "_" in meta_id else "unknown"

                meta_op = MetaOperation(
                    meta_id=meta_id,
                    name=f"Meta-operation {self._meta_operation_counter + 1}",
                    heuristic=strategy_name,
                    sub_operations=sub_ops,
                )
                meta_operations.append(meta_op)
                self._meta_operation_counter += 1

        # Add meta_operations attribute to operation_log
        operation_log.meta_operations = meta_operations

    def get_strategy_names(self) -> List[str]:
        """Get names of all configured strategies."""
        return [strategy.get_strategy_name() for strategy in self.strategies]

    def is_enabled(self) -> bool:
        """Check if detector has any enabled strategies."""
        return len(self.strategies) > 0
