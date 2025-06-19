"""
Complete basinhopping workflow tests using pytest-qt for proper signal handling.

This test suite ensures that:
1. Basinhopping calculations complete successfully
2. result_ready signal is processed correctly
3. calculation_active flag is reset properly
4. Stop functionality works correctly
5. Backward compatibility with differential_evolution is maintained
"""

import numpy as np
import pandas as pd
import pytest
from pytestqt.qtbot import QtBot

from src.core.base_signals import BaseSignals
from src.core.calculation import Calculations


class TestBasinhoppingWorkflow:
    """Complete test suite for basinhopping workflow with proper signal handling."""

    @pytest.fixture
    def signals(self):
        """Create BaseSignals instance."""
        return BaseSignals()

    @pytest.fixture
    def calculations(self, signals):
        """Create Calculations instance."""
        return Calculations(signals)

    @pytest.fixture
    def simple_experimental_data(self):
        """Create simple experimental data for testing."""
        return pd.DataFrame(
            {
                "temperature": np.linspace(27, 327, 50),  # Celsius
                "3.0": np.exp(-((np.linspace(300, 600, 50) - 450) ** 2) / 1000) * 0.8 + 0.1,
                "5.0": np.exp(-((np.linspace(300, 600, 50) - 460) ** 2) / 1000) * 0.9 + 0.1,
            }
        )

    @pytest.fixture
    def simple_reaction_scheme(self):
        """Create simple reaction scheme: A -> B."""
        return {
            "components": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                    "reaction_type": "F1",
                    "allowed_models": ["F1", "A2"],
                    "Ea": 150,
                    "log_A": 10,
                    "contribution": 1.0,
                    "Ea_min": 50.0,
                    "Ea_max": 300.0,
                    "log_A_min": 5.0,
                    "log_A_max": 15.0,
                    "contribution_min": 0.5,
                    "contribution_max": 1.0,
                }
            ],
        }

    @pytest.fixture
    def fast_basinhopping_settings(self):
        """Create fast basinhopping settings for testing."""
        return {
            "method": "basinhopping",
            "method_parameters": {
                "niter": 3,  # Very small for fast tests
                "T": 1.0,
                "stepsize": 0.3,
                "batch_size": 2,
                "minimizer_kwargs": {"method": "L-BFGS-B", "options": {"maxiter": 5}},
            },
        }

    @pytest.fixture
    def differential_evolution_settings(self):
        """Create differential evolution settings for backward compatibility tests."""
        return {
            "method": "differential_evolution",
            "method_parameters": {
                "maxiter": 5,  # Small for fast tests
                "popsize": 3,
            },
        }

    def test_basinhopping_calculation_completes(
        self,
        qtbot: QtBot,
        calculations: Calculations,
        simple_experimental_data: pd.DataFrame,
        simple_reaction_scheme: dict,
        fast_basinhopping_settings: dict,
    ):
        """Test that basinhopping calculation completes and signals are processed."""
        # Prepare calculation parameters
        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": simple_experimental_data,
            "reaction_scheme": simple_reaction_scheme,
            "calculation_settings": fast_basinhopping_settings,
        }  # Track results and signals
        results = []

        def capture_result(result_dict):
            print(f"[TEST] Captured result: {type(result_dict)}")
            results.append(result_dict)

        calculations.new_best_result.connect(capture_result)

        # Verify initial state
        assert not calculations.calculation_active, "Should start inactive"

        # Start calculation
        calculations.run_calculation_scenario(params)

        # Verify calculation started
        assert calculations.calculation_active, "Should be active after start"

        # Wait for calculation to complete using qtbot
        with qtbot.waitSignal(calculations.thread.finished, timeout=30000):
            pass  # Wait for thread to finish

        # Give time for signal processing
        qtbot.wait(100)

        # Verify final state
        assert not calculations.calculation_active, "calculation_active should be reset"
        assert len(results) > 0, "Should have captured some results"

        # Verify result structure
        last_result = results[-1]
        assert "best_mse" in last_result, "Result should contain best_mse"
        assert "params" in last_result, "Result should contain params"
        assert isinstance(last_result["best_mse"], (float, int)), "MSE should be numeric"
        assert isinstance(last_result["params"], list), "Params should be a list"
        print(f"[SUCCESS] Basinhopping completed with {len(results)} results")
        print(f"Final MSE: {last_result['best_mse']}")

    def test_basinhopping_stop_functionality(
        self,
        qtbot: QtBot,
        calculations: Calculations,
        simple_experimental_data: pd.DataFrame,
        simple_reaction_scheme: dict,
    ):
        """Test that basinhopping calculation can be stopped correctly."""
        # Long-running calculation settings
        long_running_settings = {
            "method": "basinhopping",
            "method_parameters": {
                "niter": 1000,  # Large number to ensure we can stop it
                "T": 1.0,
                "stepsize": 0.3,
                "batch_size": 2,
                "minimizer_kwargs": {"method": "L-BFGS-B"},
            },
        }

        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": simple_experimental_data,
            "reaction_scheme": simple_reaction_scheme,
            "calculation_settings": long_running_settings,
        }

        # Start calculation
        calculations.run_calculation_scenario(params)
        assert calculations.calculation_active, "Should be active after start"

        # Wait for thread to actually start and begin processing
        # We need to ensure the thread is running before trying to stop it
        qtbot.wait(100)  # Short wait for thread to start

        # Check if thread is actually running before attempting to stop
        max_attempts = 20  # Try for up to 2 seconds
        thread_running = False
        for attempt in range(max_attempts):
            if calculations.thread and calculations.thread.isRunning():
                thread_running = True
                break
            qtbot.wait(100)  # Wait 100ms between checks

        if not thread_running:
            # If thread finished too quickly, that's actually a valid scenario
            # In this case, stop_calculation should return False (no active calculation)
            stop_result = calculations.stop_calculation()
            assert stop_result is False, "Stop calculation should return False if no active thread"
            assert not calculations.calculation_active, "calculation_active should be False"
            print("[SUCCESS] Calculation completed before stop attempt - valid scenario")
            return

        # If we reach here, thread is running, so stop should succeed
        stop_result = calculations.stop_calculation()
        assert stop_result is True, "Stop calculation should return True when thread is running"

        # Wait for thread to finish
        if calculations.thread:
            with qtbot.waitSignal(calculations.thread.finished, timeout=10000):
                pass

        # Give time for signal processing
        qtbot.wait(100)

        # Verify calculation is stopped
        assert not calculations.calculation_active, "calculation_active should be reset after stop"

        print("[SUCCESS] Basinhopping stop functionality works correctly")

    def test_differential_evolution_backward_compatibility(
        self,
        qtbot: QtBot,
        calculations: Calculations,
        simple_experimental_data: pd.DataFrame,
        simple_reaction_scheme: dict,
        differential_evolution_settings: dict,
    ):
        """Test that differential_evolution still works (backward compatibility)."""
        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": simple_experimental_data,
            "reaction_scheme": simple_reaction_scheme,
            "calculation_settings": differential_evolution_settings,
        }

        # Track results
        results = []

        def capture_result(result_dict):
            results.append(result_dict)

        calculations.new_best_result.connect(capture_result)

        # Start calculation
        calculations.run_calculation_scenario(params)
        assert calculations.calculation_active, "Should be active after start"

        # Wait for calculation to complete
        with qtbot.waitSignal(calculations.thread.finished, timeout=30000):
            pass

        # Give time for signal processing
        qtbot.wait(100)

        # Verify results
        assert not calculations.calculation_active, "DE calculation should be finished"
        assert len(results) > 0, "DE should have captured some results"

        # Check result structure
        last_result = results[-1]
        assert "best_mse" in last_result
        assert "params" in last_result

        print("[SUCCESS] Differential Evolution backward compatibility works")

    def test_basinhopping_result_structure(
        self,
        qtbot: QtBot,
        calculations: Calculations,
        simple_experimental_data: pd.DataFrame,
        simple_reaction_scheme: dict,
        fast_basinhopping_settings: dict,
    ):
        """Test the structure and content of basinhopping results."""
        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": simple_experimental_data,
            "reaction_scheme": simple_reaction_scheme,
            "calculation_settings": fast_basinhopping_settings,
        }

        # Track all results
        all_results = []

        def capture_all_results(result_dict):
            all_results.append(result_dict)

        calculations.new_best_result.connect(capture_all_results)

        # Start calculation
        calculations.run_calculation_scenario(params)

        # Wait for completion
        with qtbot.waitSignal(calculations.thread.finished, timeout=30000):
            pass

        qtbot.wait(100)

        # Verify we got results
        assert len(all_results) > 0, "Should have at least one result"

        # Check each result structure
        for i, result in enumerate(all_results):
            assert isinstance(result, dict), f"Result {i} should be a dict"
            assert "best_mse" in result, f"Result {i} should have best_mse"
            assert "params" in result, f"Result {i} should have params"
            assert "iteration" in result, f"Result {i} should have iteration"

            # Check types
            assert isinstance(result["best_mse"], (float, int)), f"MSE in result {i} should be numeric"
            assert isinstance(result["params"], list), f"Params in result {i} should be a list"
            assert isinstance(result["iteration"], int), f"Iteration in result {i} should be int"

            # Check parameter structure
            assert len(result["params"]) > 0, f"Params in result {i} should not be empty"

        # Check that results show improvement (MSE should decrease or stay same)
        if len(all_results) > 1:
            mse_values = [r["best_mse"] for r in all_results]
            # MSE should be non-increasing (each result should be as good or better)
            # Allow for small floating-point precision errors
            for i in range(1, len(mse_values)):
                # Use a small tolerance to account for floating-point precision issues
                tolerance = 1e-14  # Very small tolerance for floating-point comparison
                assert mse_values[i] <= mse_values[i - 1] + tolerance, (
                    f"MSE should not increase beyond tolerance: {mse_values}, "
                    f"increase at index {i}: {mse_values[i] - mse_values[i - 1]}"
                )

        print(f"[SUCCESS] Result structure test passed with {len(all_results)} results")

    def test_basinhopping_with_multiple_reactions(
        self,
        qtbot: QtBot,
        calculations: Calculations,
        simple_experimental_data: pd.DataFrame,
        fast_basinhopping_settings: dict,
    ):
        """Test basinhopping with a more complex reaction scheme."""
        # More complex reaction scheme: A -> B -> C
        complex_scheme = {
            "components": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                    "reaction_type": "F1",
                    "allowed_models": ["F1"],
                    "Ea": 120,
                    "log_A": 8,
                    "contribution": 0.6,
                    "Ea_min": 50.0,
                    "Ea_max": 200.0,
                    "log_A_min": 5.0,
                    "log_A_max": 12.0,
                    "contribution_min": 0.3,
                    "contribution_max": 0.8,
                },
                {
                    "from": "B",
                    "to": "C",
                    "reaction_type": "F2",
                    "allowed_models": ["F2"],
                    "Ea": 180,
                    "log_A": 10,
                    "contribution": 0.4,
                    "Ea_min": 100.0,
                    "Ea_max": 250.0,
                    "log_A_min": 8.0,
                    "log_A_max": 15.0,
                    "contribution_min": 0.2,
                    "contribution_max": 0.7,
                },
            ],
        }

        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": simple_experimental_data,
            "reaction_scheme": complex_scheme,
            "calculation_settings": fast_basinhopping_settings,
        }

        # Track results
        results = []

        def capture_result(result_dict):
            results.append(result_dict)

        calculations.new_best_result.connect(capture_result)

        # Start calculation
        calculations.run_calculation_scenario(params)

        # Wait for completion
        with qtbot.waitSignal(calculations.thread.finished, timeout=45000):  # Longer timeout for complex scheme
            pass

        qtbot.wait(100)

        # Verify results
        assert not calculations.calculation_active
        assert len(results) > 0  # Check that parameters correspond to the number of reactions
        last_result = results[-1]
        params_list = last_result["params"]
        # Each reaction should have 4 parameters (logA, Ea, model_index, contribution) in new format
        expected_param_count = len(complex_scheme["reactions"]) * 4
        assert (
            len(params_list) == expected_param_count
        ), f"Expected {expected_param_count} parameters, got {len(params_list)}"

        print(f"[SUCCESS] Multi-reaction test passed with {len(params_list)} parameters")
