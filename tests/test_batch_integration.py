"""
Integration tests for BatchTakeStep with scipy.optimize.basinhopping.

This module tests the integration of BatchTakeStep with the scipy basinhopping
algorithm and compares performance with standard basinhopping.
"""

import time

import numpy as np
from scipy.optimize import basinhopping

from src.core.batch_take_step import BatchTakeStep


# Module-level functions for multiprocessing compatibility on Windows
def rosenbrock_func(x):
    """Rosenbrock function for optimization testing."""
    return sum(100.0 * (x[1:] - x[:-1] ** 2.0) ** 2.0 + (1 - x[:-1]) ** 2.0)


def rastrigin_func(x):
    """Rastrigin function for multimodal optimization testing."""
    A = 10
    n = len(x)
    return A * n + sum([(xi**2 - A * np.cos(2 * np.pi * xi)) for xi in x])


class TestBatchIntegration:
    """Integration tests for BatchTakeStep with scipy basinhopping."""

    def test_scipy_basinhopping_integration(self):
        """Test integration with scipy.optimize.basinhopping."""
        # Initial guess
        x0 = np.array([0.5, 0.5])

        # Create BatchTakeStep instance
        batch_stepper = BatchTakeStep(batch_size=4, target_func=rosenbrock_func, stepsize=0.5, seed=42)

        try:
            # Run basinhopping with BatchTakeStep
            result = basinhopping(
                func=rosenbrock_func,
                x0=x0,
                niter=20,
                T=1.0,
                take_step=batch_stepper,
                minimizer_kwargs={"method": "L-BFGS-B"},
                seed=42,
            )

            # Should find a reasonable solution
            assert result.success or result.fun < 10.0  # Rosenbrock minimum is 0
            assert isinstance(result.x, np.ndarray)
            assert result.x.shape == x0.shape

            # Should have performed evaluations
            assert batch_stepper.evaluation_count > 0

        finally:
            batch_stepper.shutdown()

    def test_performance_comparison(self):
        """Compare performance with standard basinhopping."""
        x0 = np.array([2.0, 2.0])
        niter = 10  # Small number for testing

        # Standard basinhopping
        start_time = time.time()
        standard_result = basinhopping(func=rastrigin_func, x0=x0, niter=niter, T=1.0, seed=42)
        standard_time = time.time() - start_time

        # BatchTakeStep basinhopping
        batch_stepper = BatchTakeStep(batch_size=4, target_func=rastrigin_func, stepsize=0.5, seed=42)

        try:
            start_time = time.time()
            batch_result = basinhopping(
                func=rastrigin_func, x0=x0, niter=niter, T=1.0, take_step=batch_stepper, seed=42
            )
            batch_time = time.time() - start_time

            # Both should find reasonable solutions
            assert standard_result.fun < 100  # Rastrigin minimum is 0
            assert batch_result.fun < 100

            # Print timing information for manual verification
            print(f"Standard basinhopping time: {standard_time:.3f}s")
            print(f"Batch basinhopping time: {batch_time:.3f}s")
            print(f"Speedup factor: {standard_time / batch_time:.2f}x")

            # Both methods should complete successfully
            assert isinstance(standard_result.x, np.ndarray)
            assert isinstance(batch_result.x, np.ndarray)

        finally:
            batch_stepper.shutdown()

    def test_multiprocessing_compatibility(self):
        """Test multiprocessing compatibility on Windows/Linux."""
        x0 = np.array([1.0, 1.0])

        # Test with different worker counts
        for max_workers in [1, 2, 4]:
            batch_stepper = BatchTakeStep(
                batch_size=4, target_func=rosenbrock_func, stepsize=0.5, max_workers=max_workers, seed=42
            )

            try:
                result = basinhopping(
                    func=rosenbrock_func,
                    x0=x0,
                    niter=5,  # Small number for testing
                    T=1.0,
                    take_step=batch_stepper,
                    seed=42,
                )

                # Should complete without multiprocessing errors
                assert isinstance(result.x, np.ndarray)
                assert batch_stepper.evaluation_count > 0

            finally:
                batch_stepper.shutdown()

    def test_callback_integration(self):
        """Test integration with basinhopping callback function."""
        x0 = np.array([0.5, 0.5])
        callback_calls = []

        def callback(x, f, accepted):
            callback_calls.append((x.copy(), f, accepted))
            return False  # Continue optimization

        batch_stepper = BatchTakeStep(batch_size=4, target_func=rosenbrock_func, stepsize=0.5, seed=42)

        try:
            result = basinhopping(
                func=rosenbrock_func, x0=x0, niter=5, T=1.0, take_step=batch_stepper, callback=callback, seed=42
            )  # Callback should have been called
            assert len(callback_calls) > 0

            # Each callback call should have proper format
            for x, f, accepted in callback_calls:
                assert isinstance(x, np.ndarray)
                assert isinstance(f, (int, float))
                assert isinstance(accepted, bool)

            # Verify optimization completed
            assert isinstance(result.x, np.ndarray)

        finally:
            batch_stepper.shutdown()

    def test_bounds_integration(self):
        """Test integration with bounded optimization."""
        x0 = np.array([0.5, 0.5])
        bounds = [(-2, 2), (-2, 2)]

        batch_stepper = BatchTakeStep(batch_size=4, target_func=rosenbrock_func, stepsize=0.5, seed=42)

        try:
            result = basinhopping(
                func=rosenbrock_func,
                x0=x0,
                niter=10,
                T=1.0,
                take_step=batch_stepper,
                minimizer_kwargs={"method": "L-BFGS-B", "bounds": bounds},
                seed=42,
            )

            # Solution should respect bounds
            assert np.all(result.x >= -2)
            assert np.all(result.x <= 2)

        finally:
            batch_stepper.shutdown()

    def test_different_local_minimizers(self):
        """Test with different local minimizers."""
        x0 = np.array([0.5, 0.5])

        # Test different minimizers that support bounds
        minimizers = ["L-BFGS-B", "SLSQP", "TNC"]

        for minimizer in minimizers:
            batch_stepper = BatchTakeStep(batch_size=4, target_func=rosenbrock_func, stepsize=0.5, seed=42)

            try:
                result = basinhopping(
                    func=rosenbrock_func,
                    x0=x0,
                    niter=5,
                    T=1.0,
                    take_step=batch_stepper,
                    minimizer_kwargs={"method": minimizer},
                    seed=42,
                )

                # Should complete without errors
                assert isinstance(result.x, np.ndarray)
                print(f"Minimizer {minimizer}: final value = {result.fun:.6f}")

            finally:
                batch_stepper.shutdown()

    def test_high_dimensional_optimization(self):
        """Test optimization in higher dimensions."""
        # Test with 5D problem
        x0 = np.ones(5) * 0.5

        batch_stepper = BatchTakeStep(
            batch_size=8,  # Larger batch for higher dimensions
            target_func=rastrigin_func,
            stepsize=0.5,
            seed=42,
        )

        try:
            result = basinhopping(
                func=rastrigin_func,
                x0=x0,
                niter=20,
                T=2.0,  # Higher temperature for harder problem
                take_step=batch_stepper,
                minimizer_kwargs={"method": "L-BFGS-B"},
                seed=42,
            )

            # Should handle higher dimensions without issues
            assert result.x.shape == (5,)
            assert batch_stepper.evaluation_count > 0

        finally:
            batch_stepper.shutdown()

    def test_convergence_behavior(self):
        """Test convergence behavior over multiple runs."""
        x0 = np.array([0.5, 0.5])
        results = []

        # Run multiple times with different seeds
        for seed in [42, 123, 456]:
            batch_stepper = BatchTakeStep(batch_size=4, target_func=rosenbrock_func, stepsize=0.5, seed=seed)

            try:
                result = basinhopping(func=rosenbrock_func, x0=x0, niter=20, T=1.0, take_step=batch_stepper, seed=seed)

                results.append(result.fun)

            finally:
                batch_stepper.shutdown()

        # All runs should find reasonable solutions
        assert all(fun < 10.0 for fun in results)

        # Should show some consistency (not perfect due to randomness)
        mean_result = np.mean(results)
        std_result = np.std(results)
        print(f"Convergence: mean={mean_result:.6f}, std={std_result:.6f}")

        # Standard deviation shouldn't be too large
        assert std_result < mean_result  # Reasonable consistency
