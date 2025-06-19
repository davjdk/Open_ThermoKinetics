"""
Tests for BatchTakeStep class.

This module contains comprehensive tests for the BatchTakeStep implementation,
including basic functionality, parameter validation, parallel execution,
resource management, and error handling.
"""

import concurrent.futures
import time
from threading import Event

import numpy as np
import pytest

from src.core.app_settings import MAX_BATCH_SIZE, MAX_STEPSIZE, MIN_BATCH_SIZE, MIN_STEPSIZE
from src.core.batch_take_step import BatchTakeStep


def _simple_quadratic_func(x):
    """Simple quadratic function - defined at module level for pickling."""
    return np.sum(x**2)


def _slow_quadratic_func(x):
    """Slow quadratic function - defined at module level for pickling."""
    time.sleep(0.1)  # 100ms delay
    return np.sum(x**2)


def _failing_quadratic_func(x):
    """Failing function - defined at module level for pickling."""
    if x[0] > 0.5:
        raise ValueError("Test exception")
    return np.sum(x**2)


def _biased_target_func(x):
    """Function that favors negative values - defined at module level for pickling."""
    return np.sum(x**2) + 10 * np.sum(np.maximum(0, x))


class TestBatchTakeStep:
    """Test suite for BatchTakeStep class."""

    @pytest.fixture
    def simple_target_func(self):
        """Simple quadratic function for testing."""
        return _simple_quadratic_func

    @pytest.fixture
    def slow_target_func(self):
        """Slow function for timeout testing."""
        return _slow_quadratic_func

    @pytest.fixture
    def failing_target_func(self):
        """Function that raises exceptions for error testing."""
        return _failing_quadratic_func

    def test_basic_functionality(self, simple_target_func):
        """Test basic BatchTakeStep functionality."""
        batch_size = 4
        stepsize = 0.5
        x_current = np.array([1.0, 2.0, 3.0])

        with BatchTakeStep(
            batch_size=batch_size,
            target_func=simple_target_func,
            stepsize=stepsize,
            max_workers=1,  # Use single worker to avoid multiprocessing issues in tests
            seed=42,  # For reproducibility
        ) as stepper:
            result = stepper(x_current)

            # Result should be a numpy array with same shape as input
            assert isinstance(result, np.ndarray)
            assert result.shape == x_current.shape

            # Should have evaluated batch_size proposals
            assert stepper.evaluation_count == batch_size

    def test_batch_size_validation(self, simple_target_func):
        """Test batch_size parameter validation."""
        # Test valid batch sizes
        for batch_size in [MIN_BATCH_SIZE, MAX_BATCH_SIZE, 4]:
            stepper = BatchTakeStep(batch_size=batch_size, target_func=simple_target_func, max_workers=1)
            stepper.shutdown()

        # Test invalid batch sizes
        with pytest.raises(ValueError, match="batch_size must be between"):
            BatchTakeStep(batch_size=MIN_BATCH_SIZE - 1, target_func=simple_target_func)

        with pytest.raises(ValueError, match="batch_size must be between"):
            BatchTakeStep(batch_size=MAX_BATCH_SIZE + 1, target_func=simple_target_func)

    def test_stepsize_validation(self, simple_target_func):
        """Test stepsize parameter validation."""
        # Test valid stepsizes
        for stepsize in [MIN_STEPSIZE, MAX_STEPSIZE, 0.5]:
            stepper = BatchTakeStep(batch_size=4, target_func=simple_target_func, stepsize=stepsize, max_workers=1)
            stepper.shutdown()

        # Test invalid stepsizes
        with pytest.raises(ValueError, match="stepsize must be between"):
            BatchTakeStep(batch_size=4, target_func=simple_target_func, stepsize=MIN_STEPSIZE - 0.001)

        with pytest.raises(ValueError, match="stepsize must be between"):
            BatchTakeStep(batch_size=4, target_func=simple_target_func, stepsize=MAX_STEPSIZE + 0.1)

    def test_stepsize_effect(self, simple_target_func):
        """Test that stepsize affects proposal generation."""
        x_current = np.array([0.0, 0.0])

        # Small stepsize should generate proposals close to current
        with BatchTakeStep(
            batch_size=4, target_func=simple_target_func, stepsize=0.01, max_workers=1, seed=42
        ) as small_stepper:
            small_proposals = small_stepper._generate_batch_proposals(x_current)

        # Large stepsize should generate proposals farther from current
        with BatchTakeStep(
            batch_size=4, target_func=simple_target_func, stepsize=1.0, max_workers=1, seed=42
        ) as large_stepper:
            large_proposals = large_stepper._generate_batch_proposals(x_current)

        # Calculate average distances from current point
        small_distances = [np.linalg.norm(prop - x_current) for prop in small_proposals]
        large_distances = [np.linalg.norm(prop - x_current) for prop in large_proposals]

        # Large stepsize should produce larger average distances
        assert np.mean(large_distances) > np.mean(small_distances)

    def test_concurrent_futures_executor(self, simple_target_func):
        """Test concurrent.futures ProcessPoolExecutor functionality."""
        batch_size = 4
        x_current = np.array([1.0, 2.0])

        with BatchTakeStep(
            batch_size=batch_size,
            target_func=simple_target_func,
            max_workers=1,  # Single worker for testing
        ) as stepper:
            # Initially no executor
            assert not stepper.is_active

            # After first call, executor should be created
            stepper(x_current)
            assert stepper.is_active
            assert stepper.evaluation_count == batch_size

            # Second call should reuse executor
            stepper(x_current)
            assert stepper.evaluation_count == 2 * batch_size

    def test_stop_event_interruption(self, slow_target_func):
        """Test interruption via stop_event."""
        stop_event = Event()
        batch_size = 4

        with BatchTakeStep(
            batch_size=batch_size, target_func=slow_target_func, stop_event=stop_event, max_workers=1
        ) as stepper:
            # Set stop event immediately
            stop_event.set()

            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Computation interrupted"):
                stepper(np.array([0.0, 0.0]))

    def test_resource_cleanup(self, simple_target_func):
        """Test proper resource cleanup."""
        stepper = BatchTakeStep(batch_size=4, target_func=simple_target_func, max_workers=1)

        # Create executor by making a call
        stepper(np.array([1.0, 2.0]))
        assert stepper.is_active

        # Shutdown should clean up resources
        stepper.shutdown()
        assert not stepper.is_active

        # Second shutdown should be safe
        stepper.shutdown()
        assert not stepper.is_active

    def test_context_manager(self, simple_target_func):
        """Test context manager functionality."""
        with BatchTakeStep(batch_size=4, target_func=simple_target_func, max_workers=1) as stepper:
            stepper(np.array([1.0, 2.0]))
            assert stepper.is_active

        # Should be cleaned up after context exit
        assert not stepper.is_active

    def test_error_handling(self, failing_target_func):
        """Test error handling in worker processes."""
        batch_size = 4
        # Use x_current that will cause some proposals to fail
        x_current = np.array([0.6, 0.6])  # Some proposals will have x[0] > 0.5

        with BatchTakeStep(
            batch_size=batch_size, target_func=failing_target_func, stepsize=0.1, max_workers=1, seed=42
        ) as stepper:
            # Should handle errors gracefully and return a result
            result = stepper(x_current)
            assert isinstance(result, np.ndarray)
            assert stepper.evaluation_count == batch_size

    def test_timeout_handling(self, slow_target_func):
        """Test timeout handling."""
        with BatchTakeStep(
            batch_size=2,
            target_func=slow_target_func,
            timeout=0.05,  # 50ms timeout, but function takes 100ms
            max_workers=1,
        ) as stepper:
            # Should raise TimeoutError
            with pytest.raises(concurrent.futures.TimeoutError):
                stepper(np.array([0.0, 0.0]))

    def test_max_workers_configuration(self, simple_target_func):
        """Test max_workers parameter configuration."""
        import os

        # Test default max_workers
        stepper1 = BatchTakeStep(batch_size=8, target_func=simple_target_func)
        expected_workers = min(8, os.cpu_count() or 1)
        assert stepper1.max_workers == expected_workers
        stepper1.shutdown()

        # Test explicit max_workers
        stepper2 = BatchTakeStep(batch_size=8, target_func=simple_target_func, max_workers=2)
        assert stepper2.max_workers == 2
        stepper2.shutdown()

        # Test max_workers larger than batch_size
        stepper3 = BatchTakeStep(batch_size=2, target_func=simple_target_func, max_workers=4)
        assert stepper3.max_workers == 2  # Should be limited to batch_size
        stepper3.shutdown()

    def test_reproducibility(self, simple_target_func):
        """Test reproducibility with seed."""
        x_current = np.array([1.0, 2.0])
        seed = 42

        # Run twice with same seed
        with BatchTakeStep(
            batch_size=4, target_func=simple_target_func, stepsize=0.5, max_workers=1, seed=seed
        ) as stepper1:
            result1 = stepper1(x_current)

        with BatchTakeStep(
            batch_size=4, target_func=simple_target_func, stepsize=0.5, max_workers=1, seed=seed
        ) as stepper2:
            result2 = stepper2(x_current)

        # Results should be identical
        np.testing.assert_array_equal(result1, result2)

    def test_different_dimensions(self, simple_target_func):
        """Test with different input dimensions."""
        batch_size = 4

        # Test 1D
        with BatchTakeStep(batch_size=batch_size, target_func=simple_target_func, max_workers=1, seed=42) as stepper:
            result_1d = stepper(np.array([1.0]))
            assert result_1d.shape == (1,)

        # Test 3D
        with BatchTakeStep(batch_size=batch_size, target_func=simple_target_func, max_workers=1, seed=42) as stepper:
            result_3d = stepper(np.array([1.0, 2.0, 3.0]))
            assert result_3d.shape == (3,)

        # Test higher dimensions
        with BatchTakeStep(batch_size=batch_size, target_func=simple_target_func, max_workers=1, seed=42) as stepper:
            result_5d = stepper(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
            assert result_5d.shape == (5,)

    def test_proposal_generation_bounds(self, simple_target_func):
        """Test that proposals are within expected bounds."""
        x_current = np.array([0.0, 0.0])
        stepsize = 0.5
        batch_size = 16  # Use max allowed batch size for statistical testing

        with BatchTakeStep(
            batch_size=batch_size, target_func=simple_target_func, stepsize=stepsize, max_workers=1, seed=42
        ) as stepper:
            proposals = stepper._generate_batch_proposals(x_current)

            # All proposals should be within stepsize bounds
            for proposal in proposals:
                distances = np.abs(proposal - x_current)
                assert np.all(distances <= stepsize)

    def test_best_proposal_selection(self):
        """Test that the best (minimum) proposal is selected."""
        x_current = np.array([1.0, 1.0])

        with BatchTakeStep(
            batch_size=8,
            target_func=_biased_target_func,
            stepsize=1.5,  # Large stepsize to get diverse proposals
            max_workers=1,
            seed=42,
        ) as stepper:
            # Test multiple times to increase probability of getting diverse results
            results = []
            for _ in range(3):
                result = stepper(x_current)
                result_value = _biased_target_func(result)
                results.append(result_value)

            # All results should be reasonable (function has minimum at origin)
            assert all(value < 50.0 for value in results)  # Reasonable upper bound

    def test_evaluation_count_tracking(self, simple_target_func):
        """Test evaluation count tracking."""
        batch_size = 4
        x_current = np.array([1.0, 2.0])

        with BatchTakeStep(batch_size=batch_size, target_func=simple_target_func, max_workers=1) as stepper:
            assert stepper.evaluation_count == 0

            stepper(x_current)
            assert stepper.evaluation_count == batch_size

            stepper(x_current)
            assert stepper.evaluation_count == 2 * batch_size

            stepper(x_current)
            assert stepper.evaluation_count == 3 * batch_size
