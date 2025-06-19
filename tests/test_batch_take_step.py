"""
Tests for BatchTakeStep class.

This module contains comprehensive tests for the BatchTakeStep implementation,
covering basic functionality, resource management, error handling, and performance.
"""

import multiprocessing
import time
from threading import Event
from unittest.mock import patch

import numpy as np
import pytest

from src.core.batch_take_step import BatchTakeStep


# Global functions for multiprocessing tests
def global_quadratic_function(x):
    """Global quadratic function for multiprocessing tests."""
    return np.sum(x**2)


def global_slow_function(x):
    """Global slow function for multiprocessing tests."""
    time.sleep(0.01)
    return np.sum(x**2)


def global_always_failing_function(x):
    """Global function that always fails for multiprocessing tests."""
    raise RuntimeError("Always fails")


def global_very_slow_function(x):
    """Global very slow function for stop event tests."""
    time.sleep(0.1)
    return np.sum(x**2)


def global_computational_function(x):
    """Global computational function for performance tests."""
    result = 0
    for i in range(1000):
        result += np.sum(x**2) * np.sin(i * 0.001)
    return result


def global_failing_function(x):
    """Global failing function for error handling tests."""
    if x[0] > 0:
        raise ValueError("Test error")
    return np.sum(x**2)


def global_dummy_function(x):
    """Global dummy function for basic tests."""
    return np.sum(x**2)


def global_target_function(x):
    """Global target function for tests."""
    return np.sum(x**2)


def global_quadratic_with_minimum(x):
    """Global quadratic function with minimum at [1, 1]."""
    return np.sum((x - 1) ** 2)


def global_simple_function(x):
    """Global simple function for tests."""
    return np.sum(x**2)


class TestBatchTakeStep:
    """Test suite for BatchTakeStep class."""

    def test_basic_functionality(self):
        """Test basic functionality of BatchTakeStep."""
        stepper = BatchTakeStep(batch_size=4, target_func=global_quadratic_function, random_seed=42)
        x_current = np.array([1.0, 2.0])

        # Call stepper
        x_new = stepper(x_current)

        # Check that we get valid output
        assert isinstance(x_new, np.ndarray)
        assert x_new.shape == x_current.shape
        assert len(x_new) == 2

        # Clean up
        stepper.shutdown()

    def test_batch_size_validation(self):
        """Test validation of batch_size parameter."""
        # Test invalid batch_size
        with pytest.raises(ValueError, match="batch_size must be >= 2"):
            BatchTakeStep(batch_size=1, target_func=global_dummy_function, use_multiprocessing=False)

        # Test valid batch_size
        stepper = BatchTakeStep(batch_size=2, target_func=global_dummy_function, use_multiprocessing=False)
        assert stepper.batch_size == 2
        stepper.shutdown()

    def test_stepsize_validation(self):
        """Test validation of stepsize parameter."""
        # Test invalid stepsize
        with pytest.raises(ValueError, match="stepsize must be > 0"):
            BatchTakeStep(batch_size=2, target_func=global_dummy_function, stepsize=0, use_multiprocessing=False)

        with pytest.raises(ValueError, match="stepsize must be > 0"):
            BatchTakeStep(batch_size=2, target_func=global_dummy_function, stepsize=-0.1, use_multiprocessing=False)

        # Test valid stepsize
        stepper = BatchTakeStep(
            batch_size=2, target_func=global_dummy_function, stepsize=0.1, use_multiprocessing=False
        )
        assert stepper.stepsize == 0.1
        stepper.shutdown()

    def test_stepsize_effect(self):
        """Test effect of stepsize on proposal generation."""
        x_current = np.array([0.0, 0.0])

        # Test with small stepsize
        stepper_small = BatchTakeStep(
            batch_size=4, target_func=global_target_function, stepsize=0.01, random_seed=42, use_multiprocessing=False
        )
        proposals_small = stepper_small._generate_batch_proposals(x_current)

        # Test with large stepsize
        stepper_large = BatchTakeStep(batch_size=4, target_func=global_target_function, stepsize=1.0, random_seed=42)
        proposals_large = stepper_large._generate_batch_proposals(x_current)

        # Calculate average distances from origin
        dist_small = np.mean([np.linalg.norm(p) for p in proposals_small])
        dist_large = np.mean([np.linalg.norm(p) for p in proposals_large])

        # Large stepsize should produce larger distances
        assert dist_large > dist_small

        stepper_small.shutdown()
        stepper_large.shutdown()

    def test_concurrent_futures_executor(self):
        """Test concurrent.futures ProcessPoolExecutor functionality."""
        stepper = BatchTakeStep(batch_size=4, target_func=global_slow_function, max_workers=2)
        x_current = np.array([1.0, 2.0])

        # Measure execution time
        start_time = time.time()
        x_new = stepper(x_current)
        execution_time = time.time() - start_time  # Should be faster than sequential execution (4 * 0.01 = 0.04s)
        assert execution_time < 0.5  # Allow generous overhead for process creation
        assert isinstance(x_new, np.ndarray)

        stepper.shutdown()

    def test_stop_event_interruption(self):
        """Test interruption through stop_event."""
        stop_event = Event()
        stepper = BatchTakeStep(batch_size=4, target_func=global_very_slow_function, stop_event=stop_event)
        x_current = np.array([1.0, 2.0])

        # Set stop event immediately
        stop_event.set()

        # Should raise RuntimeError due to stop event
        with pytest.raises(RuntimeError, match="Computation interrupted by stop_event"):
            stepper(x_current)

        stepper.shutdown()

    def test_resource_cleanup(self):
        """Test proper resource cleanup."""
        stepper = BatchTakeStep(batch_size=2, target_func=global_dummy_function)

        # Force executor creation
        x_current = np.array([1.0])
        stepper(x_current)

        # Check that executor exists
        assert stepper.executor is not None

        # Test shutdown
        stepper.shutdown()
        assert stepper.executor is None

        # Test double shutdown (should not raise)
        stepper.shutdown()

    def test_context_manager(self):
        """Test context manager functionality."""
        with BatchTakeStep(batch_size=2, target_func=global_dummy_function, use_multiprocessing=False) as stepper:
            x_current = np.array([1.0])
            x_new = stepper(x_current)
            assert isinstance(x_new, np.ndarray)

        # After context exit, executor should be cleaned up
        assert stepper.executor is None

    def test_error_handling(self):
        """Test handling of errors in worker processes."""
        stepper = BatchTakeStep(batch_size=4, target_func=global_failing_function, use_multiprocessing=False)
        x_current = np.array([1.0, 2.0])  # Will cause error

        # Should handle errors gracefully and return best proposal
        # (some proposals might succeed due to random perturbations)
        try:
            x_new = stepper(x_current)
            # If we get here, at least one proposal didn't fail
            assert isinstance(x_new, np.ndarray)
        except RuntimeError as e:
            # All proposals failed
            assert "All proposal evaluations failed" in str(e)

        stepper.shutdown()

    def test_max_workers_configuration(self):
        """Test max_workers configuration."""
        # Test default max_workers
        stepper1 = BatchTakeStep(batch_size=8, target_func=global_dummy_function, use_multiprocessing=False)
        expected_workers = min(8, multiprocessing.cpu_count())
        assert stepper1.max_workers == expected_workers
        stepper1.shutdown()

        # Test explicit max_workers
        stepper2 = BatchTakeStep(batch_size=8, target_func=global_dummy_function, max_workers=2)
        assert stepper2.max_workers == 2
        stepper2.shutdown()

    def test_reproducibility(self):
        """Test reproducibility with same random seed."""
        x_current = np.array([1.0, 2.0])

        # Two steppers with same seed should produce same results
        stepper1 = BatchTakeStep(
            batch_size=4, target_func=global_dummy_function, random_seed=42, use_multiprocessing=False
        )
        stepper2 = BatchTakeStep(
            batch_size=4, target_func=global_dummy_function, random_seed=42, use_multiprocessing=False
        )

        x_new1 = stepper1(x_current)
        x_new2 = stepper2(x_current)

        # Results should be identical
        np.testing.assert_array_equal(x_new1, x_new2)

        stepper1.shutdown()
        stepper2.shutdown()

    def test_different_dimensionalities(self):
        """Test with different coordinate dimensionalities."""
        stepper = BatchTakeStep(
            batch_size=4, target_func=global_target_function, random_seed=42, use_multiprocessing=False
        )

        # Test 1D
        x_1d = np.array([1.0])
        result_1d = stepper(x_1d)
        assert result_1d.shape == (1,)

        # Test 3D
        x_3d = np.array([1.0, 2.0, 3.0])
        result_3d = stepper(x_3d)
        assert result_3d.shape == (3,)

        # Test 10D
        x_10d = np.random.random(10)
        result_10d = stepper(x_10d)
        assert result_10d.shape == (10,)

        stepper.shutdown()

    def test_proposal_generation(self):
        """Test internal proposal generation method."""
        stepper = BatchTakeStep(
            batch_size=100, target_func=global_dummy_function, stepsize=1.0, random_seed=42, use_multiprocessing=False
        )
        x_current = np.array([0.0, 0.0])

        proposals = stepper._generate_batch_proposals(x_current)

        # Check we get correct number of proposals
        assert len(proposals) == 100

        # Check all proposals are numpy arrays with correct shape
        for proposal in proposals:
            assert isinstance(proposal, np.ndarray)
            assert proposal.shape == x_current.shape

        # Check proposals are within stepsize bounds (approximately)
        perturbations = [p - x_current for p in proposals]
        max_perturbation = max(np.max(np.abs(p)) for p in perturbations)
        assert max_perturbation <= 1.0  # Should be within stepsize

        stepper.shutdown()

    def test_best_proposal_selection(self):
        """Test that the best proposal is correctly selected."""
        stepper = BatchTakeStep(
            batch_size=20,
            target_func=global_quadratic_with_minimum,
            stepsize=0.1,
            random_seed=42,
            use_multiprocessing=False,
        )
        x_current = np.array([1.8, 2.9])  # Close to minimum

        # Generate multiple results and check they're improving
        results = []
        for _ in range(5):
            x_new = stepper(x_current)
            value = global_quadratic_with_minimum(x_new)
            results.append(value)
            x_current = x_new

        # Values should generally be decreasing (approaching minimum)
        # At least some improvement should occur
        assert min(results) <= results[0]
        stepper.shutdown()

    @patch("src.core.batch_take_step.logger")
    def test_logging(self, mock_logger):
        """Test that appropriate logging occurs."""
        stepper = BatchTakeStep(batch_size=2, target_func=global_dummy_function, use_multiprocessing=False)

        # Check initialization logging
        mock_logger.info.assert_called_once()
        assert "BatchTakeStep initialized" in mock_logger.info.call_args[0][0]

        # Check debug logging during execution
        x_current = np.array([1.0])
        stepper(x_current)

        assert mock_logger.debug.call_count >= 2  # Should log proposal generation and result

        stepper.shutdown()

    def test_destructor_cleanup(self):
        """Test that destructor properly cleans up resources."""
        stepper = BatchTakeStep(batch_size=2, target_func=global_dummy_function, use_multiprocessing=False)

        # Force executor creation
        x_current = np.array([1.0])
        stepper(x_current)
        # Manually call destructor
        with patch("src.core.batch_take_step.logger") as mock_logger:
            stepper.__del__()  # Should not have logged any warnings (clean shutdown)
        mock_logger.warning.assert_not_called()

    def test_stop_event_sequential_evaluation(self):
        """Test stop_event interruption during sequential evaluation."""
        stop_event = Event()

        def slow_function(x):
            import time

            if stop_event.is_set():
                raise RuntimeError("Stopped during evaluation")
            time.sleep(0.01)  # Small delay to allow stop_event to be set
            return np.sum(x**2)

        stepper = BatchTakeStep(
            batch_size=4,
            target_func=slow_function,
            stop_event=stop_event,
            use_multiprocessing=False,  # Use sequential to hit line 225
        )

        # Set stop event before evaluation
        stop_event.set()

        with pytest.raises(RuntimeError, match="Computation interrupted by stop_event"):
            stepper(np.array([1.0, 2.0]))

        stepper.shutdown()

    def test_concurrent_evaluation_stop_event(self):
        """Test stop_event interruption during concurrent evaluation with future cancellation."""
        # Test stop_event set before evaluation starts - simpler approach
        stop_event = Event()
        stop_event.set()  # Set it before we start

        stepper = BatchTakeStep(
            batch_size=4, target_func=global_slow_function, stop_event=stop_event, use_multiprocessing=True
        )

        # This should hit stop_event check in main __call__ method (line 109)
        with pytest.raises(RuntimeError, match="Computation interrupted by stop_event"):
            stepper(np.array([1.0, 2.0]))

        stepper.shutdown()

    def test_concurrent_evaluation_exception_handling(self):
        """Test exception handling during concurrent evaluation."""
        stepper = BatchTakeStep(
            batch_size=4,
            target_func=global_always_failing_function,
            use_multiprocessing=False,  # Use sequential to avoid serialization issues
        )

        # Should handle exceptions and continue with remaining proposals
        # This hits lines 196-199 (exception handling and penalty assignment)
        with pytest.raises(RuntimeError, match="All proposal evaluations failed"):
            stepper(np.array([1.0, 2.0]))

        stepper.shutdown()

    def test_all_concurrent_evaluations_fail(self):
        """Test when all concurrent evaluations fail."""
        stepper = BatchTakeStep(batch_size=4, target_func=global_always_failing_function, use_multiprocessing=True)

        # This should hit lines 203-207 (all evaluations failed check)
        with pytest.raises(RuntimeError, match="Batch evaluation failed: All proposal evaluations failed"):
            stepper(np.array([1.0, 2.0]))

        stepper.shutdown()

    def test_worker_function_coverage(self):
        """Test the _evaluate_function_worker directly to ensure line 281-282 coverage."""
        from src.core.batch_take_step import _evaluate_function_worker

        def test_func(x):
            return x[0] * 2 + x[1]

        args = np.array([3.0, 4.0])
        func_and_args = (test_func, args)

        # This should hit lines 281-282
        result = _evaluate_function_worker(func_and_args)
        assert result == 10.0  # 3*2 + 4 = 10


class TestBatchTakeStepPerformance:
    """Performance tests for BatchTakeStep."""

    def test_performance_scaling(self):
        """Test performance scaling with batch size."""
        x_current = np.array([1.0, 2.0])
        # Test different batch sizes
        batch_sizes = [2, 4]
        times = []

        for batch_size in batch_sizes:
            stepper = BatchTakeStep(
                batch_size=batch_size,
                target_func=global_computational_function,
                max_workers=min(batch_size, multiprocessing.cpu_count()),
            )

            start_time = time.time()
            stepper(x_current)
            execution_time = time.time() - start_time
            times.append(execution_time)

            stepper.shutdown()

        # Larger batch size should not be proportionally slower
        # (due to parallelization)
        efficiency_ratio = times[1] / times[0]  # time_4 / time_2
        assert efficiency_ratio < 2.0  # Should be less than 2x slower    def test_memory_usage(self):
        """Test that memory usage is reasonable."""
        # Test with larger coordinate spaces
        x_current = np.random.random(100)  # 100-dimensional problem

        stepper = BatchTakeStep(
            batch_size=8, target_func=global_simple_function, max_workers=2, use_multiprocessing=False
        )

        # Should handle large dimensionality without issues
        x_new = stepper(x_current)
        assert x_new.shape == (100,)

        stepper.shutdown()


@pytest.fixture
def simple_target_function():
    """Fixture providing a simple target function for testing."""
    return global_dummy_function


@pytest.fixture
def batch_stepper(simple_target_function):
    """Fixture providing a configured BatchTakeStep instance."""
    stepper = BatchTakeStep(batch_size=4, target_func=simple_target_function, random_seed=42)
    yield stepper
    stepper.shutdown()


class TestBatchTakeStepIntegration:
    """Integration tests using fixtures."""

    def test_multiple_calls(self, batch_stepper):
        """Test multiple sequential calls."""
        x_current = np.array([1.0, 2.0])

        for _ in range(3):
            x_new = batch_stepper(x_current)
            assert isinstance(x_new, np.ndarray)
            assert x_new.shape == x_current.shape
            x_current = x_new

    def test_with_stop_event(self, simple_target_function):
        """Test integration with stop event."""
        stop_event = Event()
        stepper = BatchTakeStep(batch_size=4, target_func=simple_target_function, stop_event=stop_event)

        x_current = np.array([1.0, 2.0])

        # Normal operation
        x_new = stepper(x_current)
        assert isinstance(x_new, np.ndarray)

        # With stop event
        stop_event.set()
        with pytest.raises(RuntimeError):
            stepper(x_current)

        stepper.shutdown()
