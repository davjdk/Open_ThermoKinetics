"""
BaseSignalsBurst strategy configuration and validation module.

This module provides configuration presets and validation functions
specifically for the BaseSignalsBurst meta-operation detection strategy.
"""

from typing import Any, Dict


def validate_base_signals_burst_config(config: Dict[str, Any]) -> None:
    """
    Validate BaseSignalsBurst strategy configuration.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ValueError: If configuration is invalid
    """
    required_params = ["time_window_ms", "min_burst_size"]

    for param in required_params:
        if param not in config:
            raise ValueError(f"BaseSignalsBurst config missing required parameter: {param}")

    # Validate temporal window
    if config["time_window_ms"] <= 0:
        raise ValueError("time_window_ms must be positive")

    # Validate minimum burst size
    if config["min_burst_size"] < 2:
        raise ValueError("min_burst_size must be at least 2")

    # Validate optional parameters
    if "max_gap_ms" in config and config["max_gap_ms"] < 0:
        raise ValueError("max_gap_ms must be non-negative")

    if "max_duration_ms" in config and config["max_duration_ms"] <= 0:
        raise ValueError("max_duration_ms must be positive")


# Configuration presets for different environments
DEVELOPMENT_CONFIG = {
    "enabled": True,
    "priority": 1,
    "time_window_ms": 50,  # More aggressive grouping for development
    "min_burst_size": 2,
    "max_gap_ms": 25,
    "max_duration_ms": 10.0,
    "include_cross_target": True,
    "debug_mode": True,  # Additional logging for development
}

PRODUCTION_CONFIG = {
    "enabled": True,
    "priority": 1,
    "time_window_ms": 100,  # Conservative settings for production
    "min_burst_size": 3,  # Larger bursts for production
    "max_gap_ms": 50,
    "max_duration_ms": 10.0,
    "include_cross_target": True,
    "debug_mode": False,
}

DEFAULT_CONFIG = {
    "enabled": True,
    "priority": 1,
    "time_window_ms": 100,
    "min_burst_size": 2,
    "max_gap_ms": 50,
    "max_duration_ms": 10.0,
    "include_cross_target": True,
    "debug_mode": False,
}


def get_config_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get a configuration preset by name.

    Args:
        preset_name: Name of the preset ('development', 'production', 'default')

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If preset name is unknown
    """
    presets = {"development": DEVELOPMENT_CONFIG, "production": PRODUCTION_CONFIG, "default": DEFAULT_CONFIG}

    if preset_name not in presets:
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {list(presets.keys())}")

    return presets[preset_name].copy()


class BaseSignalsBurstMetrics:
    """
    Metrics tracking for BaseSignalsBurst strategy performance.
    """

    def __init__(self):
        self.operations_processed = 0
        self.bursts_detected = 0
        self.average_burst_size = 0.0
        self.average_burst_duration = 0.0
        self.cross_target_bursts = 0
        self.total_duration = 0.0

    def update_metrics(self, burst_operations):
        """
        Update metrics based on detected burst.

        Args:
            burst_operations: List of SubOperationLog instances in the burst
        """
        if not burst_operations:
            return

        self.bursts_detected += 1
        self.operations_processed += len(burst_operations)

        # Calculate burst duration
        if len(burst_operations) > 1:
            burst_duration = burst_operations[-1].start_time - burst_operations[0].start_time
            self.total_duration += burst_duration
            self.average_burst_duration = self.total_duration / self.bursts_detected

        # Update average burst size
        self.average_burst_size = self.operations_processed / self.bursts_detected
        # Check for cross-target bursts
        targets = {op.target for op in burst_operations}
        if len(targets) > 1:
            self.cross_target_bursts += 1

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics.

        Returns:
            Dictionary with metric summary
        """
        return {
            "operations_processed": self.operations_processed,
            "bursts_detected": self.bursts_detected,
            "average_burst_size": round(self.average_burst_size, 2),
            "average_burst_duration_ms": round(self.average_burst_duration * 1000, 3),
            "cross_target_bursts": self.cross_target_bursts,
            "cross_target_ratio": (
                round(self.cross_target_bursts / self.bursts_detected * 100, 1) if self.bursts_detected > 0 else 0.0
            ),
        }
