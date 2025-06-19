"""
Batch-Stepper implementation for basinhopping with multiprocessing parallelization.

This module provides the BatchTakeStep class that generates batch_size random
coordinate proposals and evaluates them in parallel, returning the best proposal
to the basinhopping algorithm.
"""

import concurrent.futures
import logging
import os
from threading import Event
from typing import Callable, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class BatchTakeStep:
    """
    Batch-Stepper implementation for basinhopping with multiprocessing parallelization.

    Generates batch_size random coordinate proposals and evaluates them in parallel,
    returning the best proposal to the basinhopping algorithm.

    This implementation uses concurrent.futures.ProcessPoolExecutor for parallel
    evaluation of proposals, providing significant speedup for expensive target functions.

    Example:
        Basic usage with scipy.optimize.basinhopping:

        >>> import numpy as np
        >>> from scipy.optimize import basinhopping
        >>> from src.core.batch_take_step import BatchTakeStep
        >>>
        >>> def rosenbrock_func(x):
        ...     return sum(100.0 * (x[1:] - x[:-1] ** 2.0) ** 2.0 + (1 - x[:-1]) ** 2.0)
        >>>
        >>> x0 = np.array([0.5, 0.5])
        >>>
        >>> # Create BatchTakeStep with 4 parallel proposals
        >>> batch_stepper = BatchTakeStep(
        ...     batch_size=4,
        ...     target_func=rosenbrock_func,
        ...     stepsize=0.5,
        ...     seed=42
        ... )
        >>>
        >>> # Use with basinhopping
        >>> result = basinhopping(
        ...     func=rosenbrock_func,
        ...     x0=x0,
        ...     niter=50,
        ...     take_step=batch_stepper,
        ...     minimizer_kwargs={"method": "L-BFGS-B"},
        ...     seed=42
        ... )

        Context manager usage for automatic resource cleanup:

        >>> with BatchTakeStep(batch_size=8, target_func=rosenbrock_func) as stepper:
        ...     result = basinhopping(
        ...         func=rosenbrock_func,
        ...         x0=x0,
        ...         niter=100,
        ...         take_step=stepper
        ...     )

        With stop event for interruptible optimization:

        >>> from threading import Event
        >>>
        >>> stop_event = Event()
        >>> batch_stepper = BatchTakeStep(
        ...     batch_size=4,
        ...     target_func=rosenbrock_func,
        ...     stop_event=stop_event
        ... )
        >>>
        >>> # In another thread, you can call stop_event.set() to interrupt
    """

    def __init__(
        self,
        batch_size: int,
        target_func: Callable[[np.ndarray], float],
        stepsize: float = 0.5,
        max_workers: Optional[int] = None,
        stop_event: Optional[Event] = None,
        seed: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize BatchTakeStep.

        Args:
            batch_size: Number of parallel coordinate proposals (2-16)
            target_func: Target function for optimization (ModelBasedTargetFunction)
            stepsize: Step size for generating proposals (0.01-2.0)
            max_workers: Maximum number of processes (default: min(batch_size, cpu_count))
            stop_event: Event for interrupting computations
            seed: Random seed for reproducibility
            timeout: Timeout for individual evaluations in seconds

        Raises:
            ValueError: If batch_size is out of valid range
            ValueError: If stepsize is out of valid range
        """
        # Import here to avoid circular imports
        from .app_settings import MAX_BATCH_SIZE, MAX_STEPSIZE, MIN_BATCH_SIZE, MIN_STEPSIZE

        # Validate parameters
        if not (MIN_BATCH_SIZE <= batch_size <= MAX_BATCH_SIZE):
            raise ValueError(f"batch_size must be between {MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}")

        if not (MIN_STEPSIZE <= stepsize <= MAX_STEPSIZE):
            raise ValueError(f"stepsize must be between {MIN_STEPSIZE} and {MAX_STEPSIZE}")

        self.batch_size = batch_size
        self.target_func = target_func
        self.stepsize = stepsize
        self.stop_event = stop_event
        self.timeout = timeout

        # Configure number of workers
        if max_workers is None:
            self.max_workers = min(batch_size, os.cpu_count() or 1)
        else:
            self.max_workers = min(max_workers, batch_size)

        # Initialize random number generator
        self._rng = np.random.default_rng(seed)

        # ProcessPoolExecutor will be created on-demand
        self._executor = None
        self._evaluation_count = 0

        logger.info(
            f"BatchTakeStep initialized: batch_size={batch_size}, "
            f"stepsize={stepsize}, max_workers={self.max_workers}"
        )

    def __call__(self, x_current: np.ndarray) -> np.ndarray:
        """
        Main method called by basinhopping to generate new proposal.

        This method generates batch_size random proposals around x_current,
        evaluates them in parallel, and returns the coordinates of the best
        (minimum) proposal.

        Args:
            x_current: Current coordinates in parameter space

        Returns:
            Best coordinates from batch proposals

        Raises:
            RuntimeError: If computation is interrupted via stop_event
            concurrent.futures.TimeoutError: If evaluation timeout is exceeded
        """
        if self.stop_event and self.stop_event.is_set():
            raise RuntimeError("Computation interrupted by stop_event")

        # Generate batch proposals
        proposals = self._generate_batch_proposals(x_current)

        # Evaluate proposals in parallel
        values = self._evaluate_concurrent_futures(proposals)

        # Find best proposal
        best_idx = np.argmin(values)
        best_proposal = proposals[best_idx]
        best_value = values[best_idx]

        self._evaluation_count += self.batch_size
        logger.debug(
            f"Batch evaluation completed. Best value: {best_value:.6f}, " f"Total evaluations: {self._evaluation_count}"
        )

        return best_proposal

    def _generate_batch_proposals(self, x_current: np.ndarray) -> List[np.ndarray]:
        """
        Generate batch_size random coordinate proposals.

        Uses uniform random perturbations within stepsize bounds,
        similar to standard basinhopping step generation.

        Args:
            x_current: Current coordinates

        Returns:
            List of proposal coordinate arrays
        """
        proposals = []

        for _ in range(self.batch_size):
            # Generate random perturbation
            perturbation = self._rng.uniform(-self.stepsize, self.stepsize, size=x_current.shape)

            # Create new proposal
            proposal = x_current + perturbation
            proposals.append(proposal.copy())

        return proposals

    def _evaluate_concurrent_futures(self, proposals: List[np.ndarray]) -> List[float]:
        """
        Evaluate proposals in parallel using concurrent.futures.

        Creates a ProcessPoolExecutor on-demand and submits all proposals
        for parallel evaluation. Handles timeouts and exceptions gracefully.

        Args:
            proposals: List of coordinate proposals to evaluate

        Returns:
            List of target function values corresponding to proposals

        Raises:
            concurrent.futures.TimeoutError: If timeout is exceeded
            RuntimeError: If computation is interrupted
        """
        # Create executor on-demand
        if self._executor is None:
            self._executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)

        try:
            # Submit all proposals for evaluation
            futures = [self._executor.submit(self.target_func, proposal) for proposal in proposals]

            # Collect results with timeout handling
            values = []
            for i, future in enumerate(futures):
                if self.stop_event and self.stop_event.is_set():
                    # Cancel remaining futures
                    for remaining_future in futures[i:]:
                        remaining_future.cancel()
                    raise RuntimeError("Computation interrupted by stop_event")

                try:
                    value = future.result(timeout=self.timeout)
                    values.append(value)
                except concurrent.futures.TimeoutError:
                    logger.error(f"Timeout exceeded for proposal {i}")
                    raise
                except Exception as e:
                    logger.error(f"Error evaluating proposal {i}: {e}")
                    # Use a large penalty value for failed evaluations
                    values.append(float("inf"))

            return values

        except Exception as e:
            logger.error(f"Error in parallel evaluation: {e}")
            raise

    def shutdown(self):
        """
        Shutdown the ProcessPoolExecutor and release resources.

        This method should be called when the BatchTakeStep is no longer needed
        to ensure proper cleanup of worker processes.
        """
        if self._executor is not None:
            logger.debug("Shutting down ProcessPoolExecutor")
            self._executor.shutdown(wait=True)
            self._executor = None

    def __del__(self):
        """
        Automatic resource cleanup on object destruction.

        Ensures that ProcessPoolExecutor is properly shutdown even if
        shutdown() is not called explicitly.
        """
        try:
            self.shutdown()
        except Exception:
            # Ignore exceptions during cleanup
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.shutdown()

    @property
    def evaluation_count(self) -> int:
        """Get total number of function evaluations performed."""
        return self._evaluation_count

    @property
    def is_active(self) -> bool:
        """Check if the executor is currently active."""
        return self._executor is not None


def _evaluate_target_function(target_func: Callable, x: np.ndarray) -> float:
    """
    Helper function for multiprocessing evaluation.

    This function is defined at module level to ensure it's picklable
    for use with ProcessPoolExecutor.

    Args:
        target_func: Target function to evaluate
        x: Coordinates to evaluate

    Returns:
        Function value at x
    """
    return target_func(x)
