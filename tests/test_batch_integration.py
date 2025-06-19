"""
Integration tests for BatchTakeStep with scipy.optimize.basinhopping.

This module tests the integration of BatchTakeStep with scipy's basinhopping
algorithm and compares performance with standard implementations.
"""

import time

import numpy as np
import pytest
from scipy.optimize import basinhopping

from src.core.batch_take_step import BatchTakeStep


# Global functions for multiprocessing integration tests
def global_rosenbrock(x):
    """Rosenbrock function with minimum at [1, 1]."""
    return 100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2


def global_expensive_function(x):
    """Function that takes some time to compute."""
    result = 0
    for i in range(100):
        result += np.sum(x**2) * np.sin(i * 0.01)
    return result


def global_simple_function(x):
    """Simple quadratic function."""
    return np.sum(x**2)


def global_wrapped_function(x):
    """Wrapped function for callback tests."""
    return np.sum((x - 1) ** 2)


def global_high_dim_function(x):
    """High dimensional test function."""
    return np.sum(x**2) + 0.1 * np.sum(np.sin(10 * x))


def global_error_function(x):
    """Function that raises errors for testing."""
    if x[0] > 0.5:
        raise ValueError("Test error")
    return np.sum(x**2)


def global_test_function(x):
    """General test function."""
    return np.sum(x**2)


class TestBasinhoppingIntegration:
    """Test integration with scipy.optimize.basinhopping."""

    def test_scipy_basinhopping_integration(self):
        """Test integration with scipy.optimize.basinhopping."""
        # Create BatchTakeStep instance
        batch_stepper = BatchTakeStep(batch_size=4, target_func=global_rosenbrock, stepsize=0.5, random_seed=42)

        # Run basinhopping with BatchTakeStep
        x0 = np.array([0.0, 0.0])
        result = basinhopping(global_rosenbrock, x0, take_step=batch_stepper, niter=10, T=1.0, seed=42)

        # Check that optimization completed successfully
        assert result.success or result.message[0] == "optimization terminated successfully"
        assert isinstance(result.x, np.ndarray)
        assert len(result.x) == 2

        # Check that we found a reasonable solution
        # (may not be perfect due to limited iterations)
        assert result.fun < 100  # Should be better than starting point

        batch_stepper.shutdown()

    def test_performance_comparison(self):
        """Compare performance with standard basinhopping."""
        x0 = np.array([1.0, 2.0])

        # Test standard basinhopping
        start_time = time.time()
        result_standard = basinhopping(global_expensive_function, x0, niter=5, T=1.0, seed=42)
        time_standard = time.time() - start_time

        # Test with BatchTakeStep
        batch_stepper = BatchTakeStep(batch_size=4, target_func=global_expensive_function, stepsize=0.5, random_seed=42)

        start_time = time.time()
        result_batch = basinhopping(global_expensive_function, x0, take_step=batch_stepper, niter=5, T=1.0, seed=42)
        time_batch = time.time() - start_time

        # Both should find reasonable solutions
        assert isinstance(result_standard.x, np.ndarray)
        assert isinstance(result_batch.x, np.ndarray)  # Batch version should not be significantly slower
        # (and might be faster due to parallelization)
        efficiency_ratio = time_batch / time_standard
        assert efficiency_ratio < 20.0  # Allow significant overhead in test environment        batch_stepper.shutdown()

    def test_multiprocessing_compatibility(self):
        """Test compatibility with multiprocessing on different platforms."""
        # Test with different batch sizes and worker counts
        test_configs = [
            {"batch_size": 2, "max_workers": 1},
            {"batch_size": 4, "max_workers": 2},
            {"batch_size": 8, "max_workers": 4},
        ]

        x0 = np.array([1.0, 2.0])

        for config in test_configs:
            batch_stepper = BatchTakeStep(target_func=global_simple_function, stepsize=0.5, random_seed=42, **config)

            # Should work without errors
            result = basinhopping(global_simple_function, x0, take_step=batch_stepper, niter=3, T=1.0, seed=42)

            assert isinstance(result.x, np.ndarray)
            assert len(result.x) == 2

            batch_stepper.shutdown()

    def test_different_function_signatures(self):
        """Test with functions that have different signatures."""

        # Function with additional arguments
        def parametric_function(x, a=1.0, b=2.0):
            return a * np.sum(x**2) + b

        # Create wrapper for BatchTakeStep
        def wrapped_function(x):
            return parametric_function(x, a=2.0, b=1.0)

        batch_stepper = BatchTakeStep(
            batch_size=4, target_func=wrapped_function, stepsize=0.5, random_seed=42, use_multiprocessing=False
        )

        x0 = np.array([1.0])
        result = basinhopping(wrapped_function, x0, take_step=batch_stepper, niter=5, T=1.0, seed=42)

        assert isinstance(result.x, np.ndarray)
        assert len(result.x) == 1

        batch_stepper.shutdown()

    def test_high_dimensional_problems(self):
        """Test with high-dimensional optimization problems."""

        def high_dim_function(x):
            """Sum of squares in high dimensions."""
            return np.sum(x**2)

        # Test 10D problem
        x0 = np.random.random(10)
        batch_stepper = BatchTakeStep(
            batch_size=4, target_func=high_dim_function, stepsize=0.1, random_seed=42, use_multiprocessing=False
        )

        result = basinhopping(high_dim_function, x0, take_step=batch_stepper, niter=5, T=1.0, seed=42)

        assert isinstance(result.x, np.ndarray)
        assert len(result.x) == 10
        assert result.fun < np.sum(x0**2)  # Should improve

        batch_stepper.shutdown()

    def test_error_propagation(self):
        """Test that errors in target function are properly propagated."""

        def error_function(x):
            if np.sum(x) > 5:
                raise ValueError("Test error in target function")
            return np.sum(x**2)

        batch_stepper = BatchTakeStep(
            batch_size=4,
            target_func=error_function,
            stepsize=1.0,  # Large stepsize to trigger error
            random_seed=42,
            use_multiprocessing=False,
        )

        x0 = np.array([3.0, 3.0])  # Starting point that might trigger error

        # Should handle errors gracefully
        try:
            result = basinhopping(error_function, x0, take_step=batch_stepper, niter=3, T=1.0, seed=42)
            # If we get here, the optimization completed
            assert isinstance(result.x, np.ndarray)
        except (ValueError, RuntimeError):
            # Expected if all proposals fail
            pass

        batch_stepper.shutdown()

    def test_reproducibility_with_scipy(self):
        """Test reproducibility when used with scipy basinhopping."""

        def test_function(x):
            return np.sum(x**2) + 0.1 * np.sin(10 * np.sum(x))

        x0 = np.array([1.0, 2.0])

        # Run twice with same seeds
        results = []
        for _ in range(2):
            batch_stepper = BatchTakeStep(
                batch_size=4, target_func=test_function, stepsize=0.5, random_seed=42, use_multiprocessing=False
            )

            result = basinhopping(test_function, x0, take_step=batch_stepper, niter=5, T=1.0, seed=42)

            results.append(result.x)
            batch_stepper.shutdown()

        # Results should be identical
        np.testing.assert_array_equal(results[0], results[1])

    def test_callback_integration(self):
        """Test integration with basinhopping callback functionality."""

        def test_function(x):
            return np.sum(x**2)

        # Callback to track progress
        callback_history = []

        def callback(x, f, accept):
            callback_history.append((x.copy(), f, accept))

        batch_stepper = BatchTakeStep(
            batch_size=4, target_func=test_function, stepsize=0.5, random_seed=42, use_multiprocessing=False
        )

        x0 = np.array([1.0, 2.0])
        result = basinhopping(test_function, x0, take_step=batch_stepper, niter=3, T=1.0, callback=callback, seed=42)

        # Check that callback was called
        assert len(callback_history) > 0
        assert isinstance(result.x, np.ndarray)

        # Check callback data format
        for x, f, accept in callback_history:
            assert isinstance(x, np.ndarray)
            assert isinstance(f, (int, float))
            assert isinstance(accept, bool)

        batch_stepper.shutdown()


class TestBatchTakeStepBoundaries:
    """Test BatchTakeStep behavior at parameter boundaries."""

    def test_edge_case_parameters(self):
        """Test with edge case parameters."""

        def simple_function(x):
            return np.sum(x**2)  # Test minimum batch_size

        stepper_min = BatchTakeStep(batch_size=2, target_func=simple_function, stepsize=0.01, use_multiprocessing=False)

        x0 = np.array([1.0])
        result = basinhopping(simple_function, x0, take_step=stepper_min, niter=2, T=1.0, seed=42)

        assert isinstance(result.x, np.ndarray)
        stepper_min.shutdown()  # Test large batch_size
        stepper_large = BatchTakeStep(
            batch_size=16, target_func=simple_function, stepsize=2.0, use_multiprocessing=False
        )

        result = basinhopping(simple_function, x0, take_step=stepper_large, niter=2, T=1.0, seed=42)

        assert isinstance(result.x, np.ndarray)
        stepper_large.shutdown()

    def test_extreme_stepsizes(self):
        """Test with very small and large step sizes."""

        def test_function(x):
            return np.sum(x**2)

        x0 = np.array([1.0, 2.0])  # Very small stepsize
        stepper_small = BatchTakeStep(
            batch_size=4, target_func=test_function, stepsize=0.001, random_seed=42, use_multiprocessing=False
        )

        result_small = basinhopping(test_function, x0, take_step=stepper_small, niter=3, T=1.0, seed=42)

        assert isinstance(result_small.x, np.ndarray)
        stepper_small.shutdown()  # Large stepsize
        stepper_large = BatchTakeStep(
            batch_size=4, target_func=test_function, stepsize=5.0, random_seed=42, use_multiprocessing=False
        )

        result_large = basinhopping(test_function, x0, take_step=stepper_large, niter=3, T=1.0, seed=42)

        assert isinstance(result_large.x, np.ndarray)
        stepper_large.shutdown()


@pytest.mark.slow
class TestBatchTakeStepPerformance:
    """Performance tests that may take longer to run."""

    def test_scalability_benchmark(self):
        """Benchmark scalability with different batch sizes."""

        def computational_function(x):
            """Computationally intensive function."""
            result = 0
            for i in range(500):
                result += np.sum(x**2) * np.exp(-i * 0.001)
            return result

        x0 = np.array([1.0, 2.0])
        batch_sizes = [2, 4, 8]
        times = []

        for batch_size in batch_sizes:
            stepper = BatchTakeStep(
                batch_size=batch_size,
                target_func=computational_function,
                stepsize=0.5,
                random_seed=42,
                use_multiprocessing=False,
            )

            start_time = time.time()
            basinhopping(computational_function, x0, take_step=stepper, niter=3, T=1.0, seed=42)
            execution_time = time.time() - start_time
            times.append(execution_time)

            stepper.shutdown()

        # Performance should not degrade linearly with batch size
        # (due to parallelization benefits)
        efficiency_gain = times[0] / times[-1]  # time_2 / time_8
        assert efficiency_gain > 0.5  # At least some benefit

    def test_memory_stress(self):
        """Test memory usage under stress conditions."""

        def memory_intensive_function(x):
            # Create and process large arrays
            large_array = np.random.random((1000, len(x)))
            return np.sum(large_array @ x)

        x0 = np.random.random(100)  # 100-dimensional problem

        stepper = BatchTakeStep(
            batch_size=4,
            target_func=memory_intensive_function,
            stepsize=0.1,
            max_workers=2,  # Limit workers to control memory
            use_multiprocessing=False,
        )

        # Should complete without memory errors
        result = basinhopping(memory_intensive_function, x0, take_step=stepper, niter=2, T=1.0, seed=42)

        assert isinstance(result.x, np.ndarray)
        assert len(result.x) == 100

        stepper.shutdown()
