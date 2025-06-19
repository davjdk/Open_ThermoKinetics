"""
Worker process module for model-based calculations.

This module provides the infrastructure for running model-based calculations
in a separate process to improve GUI responsiveness and enable full CPU utilization.
"""

from typing import Any, Dict, List, Tuple

import numpy as np
from scipy.constants import R
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution

from src.core.app_settings import NUC_MODELS_TABLE
from src.core.logger_config import logger


def run_model_calc(
    target_func_data: Dict[str, Any],
    bounds: List[Tuple[float, float]],
    method_params: Dict[str, Any],
    stop_event,
    result_queue,
) -> None:
    """
    Worker function for executing model-based calculations in a separate process.
      Args:
        target_func_data: Serializable data needed to recreate the target function
        bounds: Parameter bounds for optimization
        method_params: Parameters for differential evolution algorithm
        stop_event: Event for coordinating calculation stop
        result_queue: Queue for sending results back to main process
    """

    def de_callback(xk, convergence):
        """Callback for sending intermediate results during optimization."""
        if stop_event and stop_event.is_set():
            return True  # Signal optimization to stop
        # Send current best result to main process
        try:
            best_mse = target_func.best_mse
            best_params = list(xk)
            result_queue.put(
                {"type": "intermediate", "best_mse": best_mse, "params": best_params, "convergence": convergence},
                timeout=1.0,
            )
        except Exception as e:
            logger.error(f"Error in callback: {e}")

        return False

    try:
        # Recreate target function from serializable data
        target_func = ModelBasedTargetFunctionWorker(target_func_data, stop_event)
        # Setup method parameters with callback
        method_params = method_params.copy()
        method_params["callback"] = de_callback

        # Add constraints if scheme data is available
        if "reaction_scheme" in target_func_data:
            constraints = recreate_constraints(target_func_data["reaction_scheme"])
            if constraints:
                method_params["constraints"] = constraints

        # Enable SciPy parallelization if not explicitly set
        if "workers" not in method_params or method_params["workers"] == 1:
            method_params["workers"] = -1  # Use all available cores

        logger.info(f"Starting model-based calculation with workers={method_params.get('workers', 1)}")

        # Run optimization
        result = differential_evolution(target_func, bounds, **method_params)

        # Send final result
        result_queue.put(
            {
                "type": "final_result",
                "result": result,
                "best_mse": target_func.best_mse,
                "best_params": target_func.best_params,
            }
        )

    except Exception as e:
        # Send error information
        error_msg = f"Error in worker process: {str(e)}"
        logger.error(error_msg)
        result_queue.put({"type": "error", "error": error_msg})


class ModelBasedTargetFunctionWorker:
    """
    Worker process version of ModelBasedTargetFunction that can be recreated
    from serializable data without Qt dependencies.
    """

    def __init__(self, func_data: Dict[str, Any], stop_event):
        """
        Initialize target function from serializable data.
          Args:
            func_data: Dictionary containing all necessary data to recreate the function
            stop_event: Multiprocessing event for stopping calculation
        """
        self.species_list = func_data["species_list"]
        self.reactions = func_data["reactions"]
        self.num_species = func_data["num_species"]
        self.num_reactions = func_data["num_reactions"]
        self.betas = func_data["betas"]
        self.all_exp_masses = [np.array(mass) for mass in func_data["all_exp_masses"]]
        self.exp_temperature = np.array(func_data["exp_temperature"])
        self.stop_event = stop_event

        # Initialize best tracking
        self.best_mse = float("inf")
        self.best_params = []
        self.R = R

    def __call__(self, params: np.ndarray) -> float:
        """
        Evaluate target function for given parameters.

        Args:
            params: Optimization parameters array

        Returns:
            Mean squared error value"""
        if self.stop_event and self.stop_event.is_set():
            return float("inf")

        try:
            total_mse = self._calculate_mse(params)

            # Update best result tracking
            if total_mse < self.best_mse:
                self.best_mse = total_mse
                self.best_params = params.tolist()

            return total_mse

        except Exception as e:
            logger.error(f"Error in target function evaluation: {e}")
            return float("inf")

    def _calculate_mse(self, params: np.ndarray) -> float:
        """
        Calculate MSE for all experimental conditions.

        Args:
            params: Optimization parameters

        Returns:
            Total mean squared error
        """
        total_mse = 0.0
        n = self.num_reactions

        # Normalize contribution parameters
        raw_contrib = params[3 * n : 4 * n]
        sum_contrib = np.sum(raw_contrib)
        if sum_contrib <= 0:
            return float("inf")
        norm_contrib = raw_contrib / sum_contrib  # Calculate MSE for each heating rate
        total_mse = 0.0
        for i, beta_val in enumerate(self.betas):
            if self.stop_event and self.stop_event.is_set():
                return float("inf")
            mse_i = self._integrate_ode_for_beta(beta_val, norm_contrib, params, self.all_exp_masses[i])
            total_mse += mse_i

        return total_mse

    def _integrate_ode_for_beta(
        self, beta_val: float, norm_contrib: np.ndarray, params: np.ndarray, exp_mass: np.ndarray
    ) -> float:
        """
        Integrate ODE system for a specific heating rate.

        Args:
            beta_val: Heating rate
            norm_contrib: Normalized contribution parameters
            params: All optimization parameters
            exp_mass: Experimental mass data

        Returns:
            MSE for this heating rate
        """
        try:
            T_array = self.exp_temperature
            n = self.num_reactions

            # Initial conditions
            y0 = np.zeros(self.num_species + self.num_reactions)
            if self.num_species > 0:
                y0[0] = 1.0

            # Define ODE function
            def ode_func(T, y):
                return self._ode_system(T, y, params, beta_val, n)

            # Solve ODE system
            sol = solve_ivp(ode_func, [T_array[0], T_array[-1]], y0, t_eval=T_array, method="RK45")

            if not sol.success:
                return 1e12

            # Calculate model mass from reaction rates
            rates_int = sol.y[self.num_species : self.num_species + self.num_reactions, :]
            M0 = exp_mass[0]
            Mfin = exp_mass[-1]
            int_sum = np.sum(norm_contrib[:, np.newaxis] * rates_int, axis=0)
            model_mass = M0 - (M0 - Mfin) * int_sum

            # Calculate MSE
            mse_i = np.mean((model_mass - exp_mass) ** 2)
            return mse_i

        except Exception as e:
            logger.error(f"Error in ODE integration: {e}")
            return 1e12

    def _ode_system(self, T: float, y: np.ndarray, params: np.ndarray, beta: float, n: int) -> np.ndarray:
        """
        Define the ODE system for reaction kinetics.

        Args:
            T: Temperature
            y: State vector (concentrations + integrated rates)
            params: Optimization parameters
            beta: Heating rate
            n: Number of reactions

        Returns:
            Derivatives array
        """
        dYdt = np.zeros_like(y)
        conc = y[: self.num_species]
        beta_SI = beta / 60.0  # Convert from K/min to K/s

        for i in range(n):
            # Get reaction components
            src = self.reactions[i]["from"]
            tgt = self.reactions[i]["to"]

            if src not in self.species_list or tgt not in self.species_list:
                continue

            src_index = self.species_list.index(src)
            tgt_index = self.species_list.index(tgt)
            e_value = conc[src_index]

            # Get kinetic model
            model_param_index = 2 * n + i
            model_index = int(
                np.clip(round(params[model_param_index]), 0, len(self.reactions[i]["allowed_models"]) - 1)
            )
            reaction_type = self.reactions[i]["allowed_models"][model_index]

            model = NUC_MODELS_TABLE.get(reaction_type)
            if model is None:
                f_e = e_value
            else:
                f_e = model["differential_form"](e_value)

            # Calculate rate constant (Arrhenius equation)
            logA = params[i]
            Ea = params[n + i]
            k_i = (10**logA * np.exp(-Ea * 1000 / (self.R * T))) / beta_SI

            # Calculate reaction rate
            rate = k_i * f_e

            # Update concentration derivatives
            dYdt[src_index] -= rate
            dYdt[tgt_index] += rate
            dYdt[self.num_species + i] = rate

        return dYdt


def extract_chains(scheme: dict) -> list:
    """
    Extract reaction chains from reaction scheme.

    Args:
        scheme: Reaction scheme dictionary

    Returns:
        List of reaction chains (each chain is a list of reaction indices)
    """
    components = [comp["id"] for comp in scheme["components"]]
    outgoing = {node: [] for node in components}
    incoming = {node: [] for node in components}

    for idx, reaction in enumerate(scheme["reactions"]):
        src = reaction["from"]
        dst = reaction["to"]
        outgoing[src].append((idx, dst))
        incoming[dst].append((idx, src))

    start_nodes = [node for node in components if len(incoming[node]) == 0]
    end_nodes = [node for node in components if len(outgoing[node]) == 0]

    chains = []

    def dfs(current_node, current_chain, visited):
        if current_node in visited:
            return
        visited.add(current_node)
        if current_node in end_nodes:
            chains.append(current_chain.copy())
        for edge_idx, next_node in outgoing[current_node]:
            current_chain.append(edge_idx)
            dfs(next_node, current_chain, visited)
            current_chain.pop()
        visited.remove(current_node)

    for start in start_nodes:
        dfs(start, [], set())

    return chains


def recreate_constraints(scheme_data: Dict[str, Any]) -> List[Any]:
    """
    Recreate constraints from serializable scheme data.

    Args:
        scheme_data: Reaction scheme data

    Returns:
        List of constraint objects
    """
    try:
        from scipy.optimize import NonlinearConstraint

        chains = extract_chains(scheme_data)
        num_reactions = len(scheme_data["reactions"])

        if len(chains) == 0:
            return []

        def constraint_function(X):
            contributions = X[3 * num_reactions : 4 * num_reactions]
            return np.array([np.sum(contributions[chain]) - 1.0 for chain in chains])

        return [NonlinearConstraint(constraint_function, [0.0] * len(chains), [0.0] * len(chains))]

    except Exception as e:
        logger.error(f"Error recreating constraints: {e}")
        return []


def recreate_target_function_data(
    species_list: List[str],
    reactions: List[Dict[str, Any]],
    num_species: int,
    num_reactions: int,
    betas: List[float],
    all_exp_masses: List[np.ndarray],
    exp_temperature: np.ndarray,
    reaction_scheme: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Create serializable data dictionary for target function recreation.

    Args:
        species_list: List of chemical species
        reactions: Reaction definitions
        num_species: Number of species
        num_reactions: Number of reactions
        betas: Heating rates
        all_exp_masses: Experimental mass data for each heating rate
        exp_temperature: Temperature array
        reaction_scheme: Optional reaction scheme for constraints

    Returns:
        Serializable dictionary containing all necessary data
    """
    data = {
        "species_list": species_list,
        "reactions": reactions,
        "num_species": num_species,
        "num_reactions": num_reactions,
        "betas": betas,
        "all_exp_masses": [mass.tolist() for mass in all_exp_masses],
        "exp_temperature": exp_temperature.tolist(),
    }

    if reaction_scheme is not None:
        data["reaction_scheme"] = reaction_scheme

    return data
