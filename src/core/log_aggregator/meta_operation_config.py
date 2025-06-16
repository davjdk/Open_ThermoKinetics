"""
Configuration for meta-operation detection strategies.

This module provides configuration management for meta-operation detection,
including strategy registration, parameter configuration, and factory methods.
"""

from typing import Any, Dict, List, Optional, Type

from .detection_strategies import (
    FrequencyThresholdStrategy,
    NameSimilarityStrategy,
    RequestParametersStrategy,
    SequenceCountStrategy,
    TargetClusterStrategy,
    TargetSimilarityStrategy,
    TimeWindowClusterStrategy,
)
from .meta_operation_detector import MetaOperationDetector, MetaOperationStrategy


class MetaOperationConfig:
    """
    Configuration manager for meta-operation detection strategies.

    This class handles registration of available strategies, configuration
    of strategy parameters, and factory methods for creating detectors.
    """  # Registry of available strategy classes

    STRATEGY_REGISTRY: Dict[str, Type[MetaOperationStrategy]] = {
        "time_window": TimeWindowClusterStrategy,
        "name_similarity": NameSimilarityStrategy,
        "target_similarity": TargetSimilarityStrategy,
        "request_parameters": RequestParametersStrategy,
        "sequence_count": SequenceCountStrategy,
        "frequency_threshold": FrequencyThresholdStrategy,
        "target_cluster": TargetClusterStrategy,
    }

    # Default configuration for each strategy
    DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
        "time_window": {
            "time_window_ms": 50.0,
        },
        "name_similarity": {
            "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
            "prefix_length": 3,
            "case_sensitive": False,
        },
        "target_similarity": {
            "min_sequence_length": 2,
        },
        "request_parameters": {
            "target_grouping": True,
            "kwargs_similarity": 0.7,
            "ignore_params": ["timestamp", "request_id"],
        },
        "sequence_count": {
            "min_sequence": 3,
            "operation_types": [],
            "status_filter": ["OK", "Error"],
        },
        "frequency_threshold": {
            "freq_threshold": 5,
            "freq_window_ms": 1000,
            "operation_whitelist": [],
        },
        "target_cluster": {
            "target_list": ["file_data", "series_data", "calculation_data"],
            "max_gap": 1,
            "strict_sequence": False,
            "min_cluster_size": 2,
        },
    }

    # Predefined strategy configurations based on technical specification
    PRESET_CONFIGS = {
        "basic_time_grouping": {
            "strategies": [
                {
                    "name": "time_window",
                    "priority": 1,
                    "params": {
                        "time_window_ms": 50,
                    },
                }
            ]
        },
        "enhanced_clustering": {
            "strategies": [
                {
                    "name": "time_window",
                    "priority": 1,
                    "params": {
                        "time_window_ms": 50,
                    },
                },
                {
                    "name": "target_cluster",
                    "priority": 2,
                    "params": {
                        "target_list": ["file_data", "series_data", "calculation_data"],
                        "max_gap": 1,
                        "strict_sequence": False,
                        "min_cluster_size": 2,
                    },
                },
                {
                    "name": "name_similarity",
                    "priority": 3,
                    "params": {
                        "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
                        "prefix_length": 3,
                        "case_sensitive": False,
                    },
                },
            ]
        },
        "full_detection": {
            "strategies": [
                {
                    "name": "time_window",
                    "priority": 1,
                    "params": {
                        "time_window_ms": 100,
                    },
                },
                {
                    "name": "target_cluster",
                    "priority": 2,
                    "params": {
                        "target_list": ["file_data", "series_data", "calculation_data"],
                        "max_gap": 2,
                        "strict_sequence": False,
                        "min_cluster_size": 2,
                    },
                },
                {
                    "name": "name_similarity",
                    "priority": 3,
                    "params": {
                        "name_pattern": "GET_.*|SET_.*|UPDATE_.*|LOAD_.*|SAVE_.*",
                        "prefix_length": 3,
                        "case_sensitive": False,
                    },
                },
                {
                    "name": "sequence_count",
                    "priority": 4,
                    "params": {
                        "min_sequence": 3,
                        "operation_types": [],
                        "status_filter": ["OK", "Error"],
                    },
                },
                {
                    "name": "frequency_threshold",
                    "priority": 5,
                    "params": {
                        "freq_threshold": 5,
                        "freq_window_ms": 1000,
                        "operation_whitelist": ["GET_VALUE", "SET_VALUE", "UPDATE_VALUE"],
                    },
                },
            ]
        },
        "performance_focused": {
            "strategies": [
                {
                    "name": "sequence_count",
                    "priority": 1,
                    "params": {
                        "min_sequence": 4,
                        "operation_types": ["GET_VALUE", "SET_VALUE", "UPDATE_VALUE"],
                        "status_filter": ["OK"],
                    },
                },
                {
                    "name": "frequency_threshold",
                    "priority": 2,
                    "params": {
                        "freq_threshold": 7,
                        "freq_window_ms": 500,
                        "operation_whitelist": ["GET_VALUE", "SET_VALUE"],
                    },
                },
            ]
        },
    }

    def __init__(self):
        """Initialize configuration manager."""
        self._enabled_strategies: List[str] = []
        self._strategy_configs: Dict[str, Dict[str, Any]] = {}
        self._global_enabled = True

    def enable_strategy(self, strategy_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enable a detection strategy with optional configuration.

        Args:
            strategy_name: Name of the strategy to enable
            config: Optional configuration parameters for the strategy

        Returns:
            bool: True if strategy was enabled successfully
        """
        if strategy_name not in self.STRATEGY_REGISTRY:
            return False

        if strategy_name not in self._enabled_strategies:
            self._enabled_strategies.append(strategy_name)

        # Use provided config or default
        strategy_config = config or self.DEFAULT_CONFIG.get(strategy_name, {})
        self._strategy_configs[strategy_name] = strategy_config.copy()

        return True

    def disable_strategy(self, strategy_name: str) -> bool:
        """
        Disable a detection strategy.

        Args:
            strategy_name: Name of the strategy to disable

        Returns:
            bool: True if strategy was disabled successfully
        """
        if strategy_name in self._enabled_strategies:
            self._enabled_strategies.remove(strategy_name)
            if strategy_name in self._strategy_configs:
                del self._strategy_configs[strategy_name]
            return True
        return False

    def configure_strategy(self, strategy_name: str, config: Dict[str, Any]) -> bool:
        """
        Update configuration for an enabled strategy.

        Args:
            strategy_name: Name of the strategy to configure
            config: New configuration parameters

        Returns:
            bool: True if strategy was configured successfully
        """
        if strategy_name not in self._enabled_strategies:
            return False

        if strategy_name not in self._strategy_configs:
            self._strategy_configs[strategy_name] = {}

        self._strategy_configs[strategy_name].update(config)
        return True

    def set_global_enabled(self, enabled: bool) -> None:
        """
        Enable or disable all meta-operation detection.

        Args:
            enabled: Whether meta-operation detection should be enabled
        """
        self._global_enabled = enabled

    def is_global_enabled(self) -> bool:
        """Check if meta-operation detection is globally enabled."""
        return self._global_enabled

    def get_enabled_strategies(self) -> List[str]:
        """Get list of enabled strategy names."""
        return self._enabled_strategies.copy()

    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Dict containing strategy configuration
        """
        return self._strategy_configs.get(strategy_name, {}).copy()

    def get_available_strategies(self) -> List[str]:
        """Get list of all available strategy names."""
        return list(self.STRATEGY_REGISTRY.keys())

    def create_detector(self) -> Optional[MetaOperationDetector]:
        """
        Create a MetaOperationDetector with configured strategies.

        Returns:
            MetaOperationDetector instance or None if detection is disabled
        """
        if not self._global_enabled or not self._enabled_strategies:
            return None

        strategies = []

        for strategy_name in self._enabled_strategies:
            if strategy_name in self.STRATEGY_REGISTRY:
                strategy_class = self.STRATEGY_REGISTRY[strategy_name]
                config = self._strategy_configs.get(strategy_name, {})

                try:
                    # Create strategy instance with configuration
                    strategy = strategy_class()
                    strategy.configure(**config)
                    strategies.append(strategy)
                except Exception:
                    # Skip strategies that fail to initialize
                    continue

        if not strategies:
            return None

        return MetaOperationDetector(strategies)

    def load_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary with the following structure:
                {
                    "enabled": bool,
                    "strategies": {
                        "strategy_name": {
                            "enabled": bool,
                            "config": {...}
                        }
                    }
                }
        """
        # Set global enabled state
        self._global_enabled = config_dict.get("enabled", True)

        # Clear current configuration
        self._enabled_strategies.clear()
        self._strategy_configs.clear()

        # Load strategy configurations
        strategies_config = config_dict.get("strategies", {})

        for strategy_name, strategy_data in strategies_config.items():
            if strategy_data.get("enabled", False):
                config = strategy_data.get("config", {})
                self.enable_strategy(strategy_name, config)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration to a dictionary.

        Returns:
            Dictionary containing current configuration
        """
        strategies_dict = {}

        # Include all available strategies with their enabled state
        for strategy_name in self.STRATEGY_REGISTRY.keys():
            is_enabled = strategy_name in self._enabled_strategies
            config = self._strategy_configs.get(strategy_name, {})

            strategies_dict[strategy_name] = {"enabled": is_enabled, "config": config}

        return {"enabled": self._global_enabled, "strategies": strategies_dict}

    def apply_preset_config(self, preset_name: str) -> bool:
        """
        Apply a predefined configuration preset.

        Args:
            preset_name: Name of the preset configuration to apply

        Returns:
            bool: True if preset was applied successfully
        """
        if preset_name not in self.PRESET_CONFIGS:
            return False

        preset = self.PRESET_CONFIGS[preset_name]

        # Clear current configuration
        self._enabled_strategies.clear()
        self._strategy_configs.clear()

        # Apply preset strategies in priority order
        strategies = sorted(preset["strategies"], key=lambda x: x.get("priority", 999))

        for strategy_config in strategies:
            strategy_name = strategy_config["name"]
            params = strategy_config.get("params", {})

            self.enable_strategy(strategy_name, params)

        return True

    def get_available_presets(self) -> List[str]:
        """
        Get list of available preset configuration names.

        Returns:
            List of preset names
        """
        return list(self.PRESET_CONFIGS.keys())

    def get_preset_description(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get description of a preset configuration.

        Args:
            preset_name: Name of the preset

        Returns:
            Dict containing preset configuration or None if not found
        """
        return self.PRESET_CONFIGS.get(preset_name)


# Create a global configuration instance
DEFAULT_META_OPERATION_CONFIG = MetaOperationConfig()

# Configure with reasonable defaults
DEFAULT_META_OPERATION_CONFIG.enable_strategy("time_window", {"time_window_ms": 50.0})
DEFAULT_META_OPERATION_CONFIG.enable_strategy("target_similarity", {"min_sequence_length": 3})


def get_default_detector() -> Optional[MetaOperationDetector]:
    """
    Get a detector with default configuration.

    Returns:
        MetaOperationDetector with default strategies or None if disabled
    """
    return DEFAULT_META_OPERATION_CONFIG.create_detector()


def create_detector_from_config(config_dict: Dict[str, Any]) -> Optional[MetaOperationDetector]:
    """
    Create a detector from a configuration dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        MetaOperationDetector instance or None if disabled
    """
    config = MetaOperationConfig()
    config.load_from_dict(config_dict)
    return config.create_detector()
