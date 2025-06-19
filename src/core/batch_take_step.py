"""
BatchTakeStep implementation for basinhopping with multiprocessing parallelization.

This module provides a batch-based step taking mechanism for scipy.optimize.basinhopping
that generates multiple coordinate proposals in parallel and returns the best one.
"""

import concurrent.futures
import logging
import multiprocessing
from threading import Event
from typing import Callable, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class BatchTakeStep:
    """
    Batch-Stepper implementation for basinhopping with multiprocessing parallelization.

    Generates batch_size random coordinate proposals and evaluates them in parallel,
    returning the best proposal to the basinhopping algorithm.

    This class implements the callable interface expected by scipy.optimize.basinhopping
    for custom step taking functions.

    Attributes:
        batch_size: Number of parallel coordinate proposals
        target_func: Target function for optimization (ModelBasedTargetFunction)
        stepsize: Step size for proposal generation (0.01-2.0)
        max_workers: Maximum number of processes
        stop_event: Event for computation interruption

    Example:
        >>> def target_func(x):
        ...     return np.sum(x**2)  # Simple quadratic function
        >>> stepper = BatchTakeStep(batch_size=4, target_func=target_func)
        >>> x_current = np.array([1.0, 2.0])
        >>> x_new = stepper(x_current)
        >>> print(f"New proposal: {x_new}")"""

    def __init__(
        self,
        batch_size: int,
        target_func: Callable,
        stepsize: float = 0.5,
        max_workers: Optional[int] = None,
        stop_event: Optional[Event] = None,
        random_seed: Optional[int] = None,
        use_multiprocessing: bool = True,
    ):
        """
        Initialize BatchTakeStep.

        Args:
            batch_size: Number of parallel coordinate proposals
            target_func: Target function for optimization (ModelBasedTargetFunction)
            stepsize: Step size for proposal generation (0.01-2.0)
            max_workers: Maximum number of processes (default: min(batch_size, cpu_count))
            stop_event: Event for computation interruption
            random_seed: Seed for reproducible random number generation

        Raises:
            ValueError: If batch_size < 2 or stepsize <= 0
        """
        if batch_size < 2:
            raise ValueError(f"batch_size must be >= 2, got {batch_size}")
        if stepsize <= 0:
            raise ValueError(f"stepsize must be > 0, got {stepsize}")

        self.batch_size = batch_size
        self.target_func = target_func
        self.stepsize = stepsize
        self.stop_event = stop_event or Event()
        self.use_multiprocessing = use_multiprocessing

        # Configure multiprocessing
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = max_workers if max_workers is not None else min(batch_size, cpu_count)
        self.executor = None

        # Initialize random number generator
        self.rng = np.random.default_rng(random_seed)

        logger.info(
            f"BatchTakeStep initialized: batch_size={batch_size}, "
            f"stepsize={stepsize}, max_workers={self.max_workers}"
        )

    def __call__(self, x_current: np.ndarray) -> np.ndarray:
        """
        Main method called by basinhopping to generate new proposal.

        This method generates batch_size random proposals around x_current,
        evaluates them in parallel, and returns the coordinates with the
        lowest function value.

        Args:
            x_current: Current coordinates in parameter space

        Returns:
            Best coordinates from batch proposals

        Raises:
            RuntimeError: If computation is interrupted or all evaluations fail
        """
        if self.stop_event.is_set():
            raise RuntimeError("Computation interrupted by stop_event")

        logger.debug(f"Generating {self.batch_size} proposals from {x_current}")

        # Generate batch proposals
        proposals = self._generate_batch_proposals(x_current)  # Evaluate proposals in parallel or sequentially
        try:
            if self.use_multiprocessing:
                values = self._evaluate_concurrent_futures(proposals)
            else:
                values = self._evaluate_sequential(proposals)
        except Exception as e:
            logger.error(f"Failed to evaluate proposals: {e}")
            raise RuntimeError(f"Batch evaluation failed: {e}") from e

        # Find best proposal
        best_idx = np.argmin(values)
        best_proposal = proposals[best_idx]
        best_value = values[best_idx]

        logger.debug(f"Best proposal: {best_proposal} with value {best_value}")
        return best_proposal

    def _generate_batch_proposals(self, x_current: np.ndarray) -> List[np.ndarray]:
        """
        Generate batch_size random coordinate proposals.

        Uses uniform random perturbations within stepsize bounds,
        similar to standard basinhopping step taking.

        Args:
            x_current: Current coordinates

        Returns:
            List of proposed coordinate arrays
        """
        proposals = []

        for _ in range(self.batch_size):
            # Generate random perturbation: x_new = x_current + uniform(-stepsize, stepsize)
            perturbation = self.rng.uniform(low=-self.stepsize, high=self.stepsize, size=x_current.shape)
            x_new = x_current + perturbation
            proposals.append(x_new.copy())

        return proposals

    def _evaluate_concurrent_futures(self, proposals: List[np.ndarray]) -> List[float]:
        """
        Evaluate proposals in parallel using concurrent.futures.

        Creates a ProcessPoolExecutor for parallel function evaluation
        with proper resource management and exception handling.

        Args:
            proposals: List of coordinate arrays to evaluate

        Returns:
            List of function values for each proposal

        Raises:
            RuntimeError: If computation is interrupted or executor fails
        """
        values = []

        # Create executor if not exists
        if self.executor is None:
            self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)

        try:
            # Submit all tasks
            future_to_proposal = {
                self.executor.submit(self.target_func, proposal): i for i, proposal in enumerate(proposals)
            }
            # Collect results with interruption support
            values = [None] * len(proposals)

            for future in concurrent.futures.as_completed(future_to_proposal):
                if self.stop_event.is_set():
                    # Cancel remaining futures
                    for f in future_to_proposal:
                        f.cancel()
                    raise RuntimeError("Computation interrupted by stop_event")

                proposal_idx = future_to_proposal[future]
                try:
                    values[proposal_idx] = future.result()
                except Exception as e:
                    logger.error(f"Proposal {proposal_idx} evaluation failed: {e}")
                    # Use a large penalty value for failed evaluations
                    values[proposal_idx] = float("inf")

            # Check if all evaluations failed
            if all(v == float("inf") for v in values):
                raise RuntimeError("All proposal evaluations failed")

        except Exception as e:
            logger.error(f"Concurrent evaluation failed: {e}")
            raise

        return values

    def _evaluate_sequential(self, proposals: List[np.ndarray]) -> List[float]:
        """
        Evaluate proposals sequentially (for testing with non-picklable functions).

        Args:
            proposals: List of coordinate arrays to evaluate

        Returns:
            List of function values for each proposal
        """
        values = []

        for i, proposal in enumerate(proposals):
            if self.stop_event.is_set():
                raise RuntimeError("Computation interrupted by stop_event")

            try:
                value = self.target_func(proposal)
                values.append(value)
            except Exception as e:
                logger.error(f"Proposal {i} evaluation failed: {e}")
                values.append(float("inf"))

        # Check if all evaluations failed
        if all(v == float("inf") for v in values):
            raise RuntimeError("All proposal evaluations failed")

        return values

    def shutdown(self):
        """
        Release executor resources.

        Should be called when BatchTakeStep is no longer needed
        to ensure proper cleanup of worker processes.
        """
        if self.executor is not None:
            logger.debug("Shutting down ProcessPoolExecutor")
            self.executor.shutdown(wait=True)
            self.executor = None

    def __del__(self):
        """Automatic resource cleanup on object destruction."""
        try:
            self.shutdown()
        except Exception as e:
            logger.warning(f"Error during BatchTakeStep cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.shutdown()


def _evaluate_function_worker(func_and_args):
    """
    Worker function for multiprocessing evaluation.

    This function is used as a target for ProcessPoolExecutor
    to evaluate the target function with given arguments.

    Args:
        func_and_args: Tuple of (function, arguments)

    Returns:
        Function evaluation result
    """
    func, args = func_and_args
    return func(args)
