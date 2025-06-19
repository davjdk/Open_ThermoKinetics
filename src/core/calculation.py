from multiprocessing import Manager
from typing import Callable, Optional

from core.base_signals import BaseSlots
from core.calculation_results_strategies import BestResultStrategy, DeconvolutionStrategy, ModelBasedCalculationStrategy
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from scipy.optimize import OptimizeResult, differential_evolution

from src.core.app_settings import OperationType
from src.core.calculation_scenarios import SCENARIO_REGISTRY, make_de_callback
from src.core.calculation_thread import CalculationThread
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console
from src.core.model_calc_proxy import ModelCalcProxy


class Calculations(BaseSlots):
    new_best_result = pyqtSignal(dict)

    def __init__(self, signals):
        super().__init__(actor_name="calculations", signals=signals)
        self.thread: Optional[CalculationThread] = None
        self.best_combination: Optional[tuple] = None
        self.best_mse: float = float("inf")
        self.new_best_result.connect(self.handle_new_best_result)
        self.calc_params = {}
        self.mse_history = []
        self.calculation_active = False

        self.manager = Manager()
        self.stop_event = self.manager.Event()

        # Initialize subprocess proxy for model-based calculations
        self.model_calc_proxy = ModelCalcProxy(self)

        self.deconvolution_strategy = DeconvolutionStrategy(self)
        self.model_based_calculation_strategy = ModelBasedCalculationStrategy(self)
        self.result_strategy: Optional[BestResultStrategy] = None

    def set_result_strategy(self, strategy_type: str):
        if strategy_type == "deconvolution":
            self.result_strategy = self.deconvolution_strategy
        elif strategy_type == "model_based_calculation":
            self.result_strategy = self.model_based_calculation_strategy
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    def start_calculation_thread(self, func: Callable, *args, **kwargs) -> None:
        self.stop_event.clear()
        self.calculation_active = True
        self.thread = CalculationThread(func, *args, **kwargs)
        self.thread.result_ready.connect(self._calculation_finished)
        self.thread.start()

    def stop_calculation(self):
        """Modified method to handle both subprocess and thread calculations."""
        # Check for active subprocess first
        if self.model_calc_proxy.process and self.model_calc_proxy.process.is_alive():
            logger.info("Stopping current calculation (subprocess).")
            self.model_calc_proxy.stop_process()
            self.calculation_active = False
            self.result_strategy = None
            console.log("\nCalculation process has been requested to stop.")
            return True

        # Existing logic for QThread
        if self.thread and self.thread.isRunning():
            logger.info("Stopping current calculation (thread)...")
            self.stop_event.set()
            self.calculation_active = False
            self.result_strategy = None
            self.thread.requestInterruption()
            console.log("\nCalculation thread has been requested to stop. Wait for it to finish.")
            return True

        logger.info("No active calculation to stop.")
        console.log("No active calculation to stop.")
        return False

    @pyqtSlot(dict)
    def process_request(self, params: dict):
        operation = params.get("operation")
        response = params.copy()
        if operation == OperationType.STOP_CALCULATION:
            response["data"] = self.stop_calculation()

        response["target"], response["actor"] = response["actor"], response["target"]
        self.signals.response_signal.emit(response)

    @pyqtSlot(dict)
    def run_calculation_scenario(self, params: dict):
        """Modified method to support subprocess for model-based calculations."""
        self.calc_params = params.copy()
        scenario_key = params.get("calculation_scenario")
        if not scenario_key:
            logger.error("No 'calculation_scenario' provided in params.")
            return

        if scenario_key == "model_based_calculation":
            # New path through subprocess
            self._run_model_based_subprocess(params)
        else:
            # Existing path through QThread
            self._run_thread_calculation(params)

    def _run_model_based_subprocess(self, params: dict):
        """
        Run model-based calculation in separate process.

        Args:
            params: Calculation parameters with scenario settings
        """
        try:
            scenario_cls = SCENARIO_REGISTRY.get("model_based_calculation")
            if not scenario_cls:
                logger.error("ModelBasedScenario not found in registry")
                return

            scenario_instance = scenario_cls(params, self)

            # Prepare bounds and validate
            bounds = scenario_instance.get_bounds()
            for lb, ub in bounds:
                if ub < lb:
                    console.log("Invalid bounds: upper bound is less than lower bound.")
                    raise ValueError("Invalid bounds: upper bound is less than lower bound.")

            # Prepare constraints for subprocess
            constraints = scenario_instance.get_constraints()

            # Prepare target function data for subprocess
            target_func_data = self._prepare_target_function_for_subprocess(scenario_instance)

            # Prepare algorithm parameters
            method_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()
            if constraints:
                method_params["constraints"] = constraints

            # Set result strategy
            strategy_type = scenario_instance.get_result_strategy_type()
            self.set_result_strategy(strategy_type)

            # Start subprocess calculation
            success = self.model_calc_proxy.start_process(target_func_data, bounds, method_params)
            if success:
                self.calculation_active = True
                logger.info("Model-based calculation started in subprocess")
                console.log("Model-based calculation started in subprocess...")
            else:
                logger.error("Failed to start model-based calculation subprocess")
                console.log("Failed to start model-based calculation subprocess")

        except Exception as e:
            logger.error(f"Error setting up model-based subprocess: {e}")
            console.log(f"Error setting up model-based subprocess: {e}")

    def _run_thread_calculation(self, params: dict):
        """Existing logic for other calculation types."""
        scenario_key = params.get("calculation_scenario")
        scenario_cls = SCENARIO_REGISTRY.get(scenario_key)
        if not scenario_cls:
            logger.error(f"Unknown calculation scenario: {scenario_key}")
            return

        scenario_instance = scenario_cls(params, self)
        try:
            bounds = scenario_instance.get_bounds()
            for lb, ub in bounds:
                if ub < lb:
                    console.log("Invalid bounds: upper bound is less than lower bound.")
                    raise ValueError("Invalid bounds: upper bound is less than lower bound.")
            # NEW: Pass calculations instance to scenario
            target_function = scenario_instance.get_target_function(calculations_instance=self)
            optimization_method = scenario_instance.get_optimization_method()
            strategy_type = scenario_instance.get_result_strategy_type()
            self.set_result_strategy(strategy_type)

            if optimization_method == "differential_evolution":
                calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()

                if scenario_key == "model_based_calculation":
                    calc_params["constraints"] = scenario_instance.get_constraints()
                    calc_params["callback"] = make_de_callback(target_function, self)

                self.start_differential_evolution(bounds=bounds, target_function=target_function, **calc_params)
            elif optimization_method == "basinhopping" and scenario_key == "model_based_calculation":
                # New basinhopping support for ModelBasedScenario
                calc_params = params.get("calculation_settings", {}).get("method_parameters", {}).copy()

                # Use ModelBasedScenario's new run method for basinhopping
                self.start_basinhopping(scenario_instance, bounds, target_function, calc_params)
            else:
                logger.error(f"Unsupported optimization method: {optimization_method}")

        except Exception as e:
            logger.error(f"Error setting up scenario '{scenario_key}': {e}")
            console.log(f"Error setting up scenario '{scenario_key}': {e}")

    def _prepare_target_function_for_subprocess(self, scenario_instance):
        """
        Prepare target function data for use in subprocess.

        Ensures serializability and compatibility with multiprocessing.
        """
        try:
            # Get parameters needed to recreate target function in subprocess
            scheme = scenario_instance.params.get("reaction_scheme")
            experimental_data = scenario_instance.params.get("experimental_data")

            if not scheme or experimental_data is None:
                raise ValueError("Missing reaction_scheme or experimental_data")

            target_func_data = {
                "reaction_scheme": scheme,
                "experimental_data": experimental_data,
                "type": "model_based",
            }

            # Test serializability
            import pickle

            pickle.dumps(target_func_data)

            logger.debug("Target function data prepared for subprocess")
            return target_func_data

        except Exception as e:
            logger.error(f"Target function data is not serializable: {e}")
            raise ValueError(f"Target function cannot be used in subprocess: {e}")

    def _prepare_constraints_for_subprocess(self, scenario_instance):
        """
        Prepare constraints for subprocess.

        If constraints are not serializable, pass data for recreation.
        """
        constraints = scenario_instance.get_constraints()

        if not constraints:
            return None

        try:
            import pickle

            pickle.dumps(constraints)
            return constraints
        except Exception as e:
            logger.warning(f"Constraints not serializable, will recreate in subprocess: {e}")
            # Pass reaction scheme data for constraint recreation
            reaction_scheme = scenario_instance.params.get("reaction_scheme")
            return {"recreate_from_scheme": reaction_scheme}

    def start_differential_evolution(self, bounds, target_function, **kwargs):
        """
        Backward compatible method for starting differential evolution.

        Automatically determines whether to use subprocess or thread.
        """
        if "scenario_key" in kwargs and kwargs["scenario_key"] == "model_based_calculation":
            # New path - handled by run_calculation_scenario
            logger.debug("Differential evolution routed through subprocess")
        else:
            # Existing path
            self.start_calculation_thread(
                differential_evolution,
                target_function,
                bounds=bounds,
                **kwargs,
            )

    def start_basinhopping(self, scenario_instance, bounds, target_function, calc_params):
        """
        Start basinhopping optimization for ModelBasedScenario.

        Args:
            scenario_instance: ModelBasedScenario instance
            bounds: Parameter bounds
            target_function: Target function to optimize
            calc_params: Optimization parameters
        """
        try:
            logger.info("Starting basinhopping optimization")

            # Use scenario's run method with basinhopping
            result = scenario_instance.run(
                target_func=target_function, bounds=bounds, method_params=calc_params, stop_event=self.stop_event
            )

            # Handle the result
            self._calculation_finished(result)

        except Exception as e:
            logger.error(f"Error in basinhopping optimization: {e}")
            self._calculation_finished(e)

    @pyqtSlot(object)
    def _calculation_finished(self, result):
        try:
            if isinstance(result, Exception):
                if str(result) == "array must not contain infs or NaNs":
                    console.log("\nСalculation was successfully terminated.")
                else:
                    logger.error(f"Calculation error: {result}")
            elif isinstance(result, OptimizeResult):
                x = result.x
                fun = result.fun
                logger.info(f"Calculation completed. Optimal parameters: {x}, fun={fun}")
                console.log(f"Calculation completed. Optimal parameters: {x}, fun={fun}")
                self.best_mse = float("inf")
                self.best_combination = None
            else:
                logger.info("Calculation finished with a non-OptimizeResult object.")
                console.log(f"Calculation result: {result}")
        except Exception as e:
            logger.error(f"Error processing the result: {e}")
            console.log("An error occurred while processing the result. Check logs for details.")

        self.calculation_active = False
        self.result_strategy = None
        self.best_mse = float("inf")
        self.best_combination = None
        self.mse_history = []
        self.handle_request_cycle("main_window", OperationType.CALCULATION_FINISHED)

    @pyqtSlot(dict)
    def handle_new_best_result(self, result: dict):
        try:
            logger.debug(f"Handling new best result: {result}")
            if self.result_strategy:
                self.result_strategy.handle(result)
            else:
                logger.warning("No strategy set. Best result will not be handled.")
        except Exception as e:
            logger.error(f"Error handling new best result: {e}")
            console.log(f"Error handling new best result: {e}")
