"""
Simplified integration test for basinhopping workflow.

Tests the core basinhopping functionality without complex data structures.
"""

import numpy as np
import pandas as pd

from src.core.base_signals import BaseSignals
from src.core.calculation import Calculations


class TestBasinhoppingSimpleIntegration:
    """Simplified integration tests for basinhopping workflow."""

    def setup_method(self):
        """Setup test fixtures for integration tests."""
        # Create Qt signals
        self.signals = BaseSignals()

        # Create calculations instance
        self.calculations = Calculations(self.signals)

    def test_basinhopping_calculation_workflow(self):
        """Test basinhopping calculation through Calculations class."""
        # Create simple experimental data
        exp_data = pd.DataFrame(
            {
                "temperature": np.linspace(27, 327, 50),  # Celsius
                "3.0": np.exp(-((np.linspace(300, 600, 50) - 450) ** 2) / 1000) * 0.8 + 0.1,
                "5.0": np.exp(-((np.linspace(300, 600, 50) - 460) ** 2) / 1000) * 0.9 + 0.1,
            }
        )

        # Simple reaction scheme: A -> B
        reaction_scheme = {
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

        # Basinhopping calculation settings
        calculation_settings = {
            "method": "basinhopping",
            "method_parameters": {
                "niter": 5,  # Very small for fast tests
                "T": 1.0,
                "stepsize": 0.3,
                "batch_size": 2,
                "minimizer_kwargs": {"method": "L-BFGS-B", "options": {"maxiter": 5}},
            },
        }

        # Prepare calculation parameters
        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": exp_data,
            "reaction_scheme": reaction_scheme,
            "calculation_settings": calculation_settings,
        }

        # Mock result capturing
        results = []

        def capture_result(result_dict):
            results.append(result_dict)

        self.calculations.new_best_result.connect(capture_result)  # Add signal monitoring
        calculation_finished_received = []

        def on_calculation_finished(result):
            print(f"[TEST] _calculation_finished signal received with result: {type(result)}")
            calculation_finished_received.append(result)

        # Run calculation
        self.calculations.run_calculation_scenario(params)

        # Wait for calculation to complete
        if self.calculations.thread:
            print("[TEST] Thread created, waiting for completion...")
            # Connect to the thread's result_ready signal for monitoring
            self.calculations.thread_result_ready = []

            def on_thread_result(result):
                print(f"[TEST] thread result_ready signal received: {type(result)}")
                self.calculations.thread_result_ready.append(result)

            self.calculations.thread.result_ready.connect(on_thread_result)

            finished = self.calculations.thread.wait(30000)  # 30 second timeout
            print(f"[TEST] Thread finished: {finished}")
            print(f"[TEST] Thread is running: {self.calculations.thread.isRunning()}")
            print(f"[TEST] Thread is finished: {self.calculations.thread.isFinished()}")
            print(f"[TEST] calculation_active: {self.calculations.calculation_active}")
            print(f"[TEST] Thread results received: {len(self.calculations.thread_result_ready)}")

        # Verify results
        assert not self.calculations.calculation_active, "Calculation should be finished"
        assert len(results) > 0, "Should have captured some results"  # Check result structure
        last_result = results[-1]
        assert "best_mse" in last_result
        assert "params" in last_result
        assert isinstance(last_result["best_mse"], (float, int))
        assert isinstance(last_result["params"], list)

        print("\\nBasinhopping test completed successfully!")
        print(f"Results captured: {len(results)}")
        print(f"Final MSE: {last_result['best_mse']}")
        print(f"Parameters: {last_result['params']}")

    def test_stop_basinhopping_calculation(self):
        """Test stopping basinhopping calculation."""
        # Simple experimental data
        exp_data = pd.DataFrame(
            {
                "temperature": np.linspace(27, 327, 20),
                "5.0": np.random.random(20),
            }
        )

        # Simple reaction scheme
        reaction_scheme = {
            "components": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                    "reaction_type": "F1",
                    "allowed_models": ["F1"],
                    "Ea_min": 50.0,
                    "Ea_max": 300.0,
                    "log_A_min": 5.0,
                    "log_A_max": 15.0,
                    "contribution_min": 0.5,
                    "contribution_max": 1.0,
                }
            ],
        }

        # Long-running calculation settings
        calculation_settings = {
            "method": "basinhopping",
            "method_parameters": {
                "niter": 1000,  # Large number to ensure we can stop it
                "T": 1.0,
                "stepsize": 0.3,
                "batch_size": 2,
            },
        }

        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": exp_data,
            "reaction_scheme": reaction_scheme,
            "calculation_settings": calculation_settings,
        }

        # Start calculation
        self.calculations.run_calculation_scenario(params)

        # Wait a bit to let calculation start
        import time

        time.sleep(0.5)

        # Stop calculation
        stop_result = self.calculations.stop_calculation()
        assert stop_result is True, "Stop calculation should return True"

        # Wait for thread to finish
        if self.calculations.thread:
            self.calculations.thread.wait(10000)  # 10 second timeout

        # Verify calculation is stopped
        assert not self.calculations.calculation_active, "Calculation should be stopped"

    def test_differential_evolution_still_works(self):
        """Test that differential_evolution still works (backward compatibility)."""
        # Simple experimental data
        exp_data = pd.DataFrame(
            {
                "temperature": np.linspace(27, 327, 30),
                "5.0": np.exp(-((np.linspace(300, 600, 30) - 450) ** 2) / 1000) * 0.8 + 0.1,
            }
        )

        # Simple reaction scheme
        reaction_scheme = {
            "components": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {
                    "from": "A",
                    "to": "B",
                    "reaction_type": "F1",
                    "allowed_models": ["F1"],
                    "Ea_min": 50.0,
                    "Ea_max": 300.0,
                    "log_A_min": 5.0,
                    "log_A_max": 15.0,
                    "contribution_min": 0.5,
                    "contribution_max": 1.0,
                }
            ],
        }

        # Differential evolution settings
        calculation_settings = {
            "method": "differential_evolution",
            "method_parameters": {
                "maxiter": 5,  # Small for fast tests
                "popsize": 3,
            },
        }

        params = {
            "calculation_scenario": "model_based_calculation",
            "experimental_data": exp_data,
            "reaction_scheme": reaction_scheme,
            "calculation_settings": calculation_settings,
        }

        # Mock result capturing
        results = []

        def capture_result(result_dict):
            results.append(result_dict)

        self.calculations.new_best_result.connect(capture_result)

        # Run calculation
        self.calculations.run_calculation_scenario(params)

        # Wait for calculation to complete
        if self.calculations.thread:
            self.calculations.thread.wait(30000)

        # Verify results
        assert not self.calculations.calculation_active, "DE calculation should be finished"
        assert len(results) > 0, "DE should have captured some results"

        # Check result structure
        last_result = results[-1]
        assert "best_mse" in last_result
        assert "params" in last_result

        print("\\nDifferential Evolution test completed successfully!")
        print(f"Results captured: {len(results)}")
        print(f"Final MSE: {last_result['best_mse']}")
