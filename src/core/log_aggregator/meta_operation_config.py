"""
Configuration for meta-operation detection strategies.

This module provides configuration management for meta-operation detection,
including strategy registration, parameter configuration, and factory methods.
"""

from typing import Any, Dict, List, Optional, Type

from .detection_strategies import (
    BaseSignalsBurstStrategy,
    NameSimilarityStrategy,
    SequenceCountStrategy,
    TargetClusterStrategy,
    TimeWindowStrategy,
)
from .meta_operation_detector import MetaOperationDetector, MetaOperationStrategy


class MetaOperationConfig:
    """
    Configuration manager for meta-operation detection strategies.

    This class handles registration of available strategies, configuration
    of strategy parameters, and factory methods for creating detectors."""  # Registry of available strategy classes

    STRATEGY_REGISTRY: Dict[str, Type[MetaOperationStrategy]] = {
        "time_window": TimeWindowStrategy,
        "name_similarity": NameSimilarityStrategy,
        "target_cluster": TargetClusterStrategy,
        "sequence_count": SequenceCountStrategy,
        "base_signals_burst": BaseSignalsBurstStrategy,
    }  # Default configuration for each strategy
    DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
        "time_window": {
            "window_ms": 50.0,
            "min_cluster_size": 2,
        },
        "name_similarity": {
            "min_cluster_size": 2,
        },
        "target_cluster": {
            "min_cluster_size": 2,
        },
        "sequence_count": {
            "min_sequence_length": 3,
        },
        "base_signals_burst": {
            "window_ms": 100.0,  # Временное окно кластеризации (мс)
            "min_cluster_size": 2,  # Минимум base_signals операций в кластере
            "include_noise": True,  # Включать промежуточные операции как шум
            "max_cluster_duration_ms": 5000,  # Максимальная длительность кластера (мс)
            "priority": 1,  # Высокий приоритет (выполняется первой)
        },
    }  # Predefined strategy configurations based on technical specification
    PRESET_CONFIGS = {
        "basic_time_grouping": {
            "strategies": [
                {
                    "name": "time_window",
                    "priority": 1,
                    "params": {
                        "window_ms": 50,
                    },
                }
            ]
        },
        "comprehensive": {
            "strategies": [
                {
                    "name": "base_signals_burst",
                    "priority": 1,  # Высокий приоритет
                    "params": {
                        "window_ms": 100.0,
                        "min_cluster_size": 2,
                        "include_noise": True,
                        "max_cluster_duration_ms": 5000,
                    },
                },
                {
                    "name": "time_window",
                    "priority": 2,  # Выполняется после base_signals_burst
                    "params": {
                        "window_ms": 50.0,
                        "min_cluster_size": 2,
                    },
                },
                {
                    "name": "target_cluster",
                    "priority": 3,
                    "params": {
                        "target_list": ["file_data", "series_data", "calculation_data"],
                        "max_gap": 2,
                        "strict_sequence": False,
                        "min_cluster_size": 2,
                    },
                },
                {
                    "name": "name_similarity",
                    "priority": 4,
                    "params": {
                        "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
                        "prefix_length": 3,
                        "case_sensitive": False,
                        "min_cluster_size": 2,
                    },
                },
                {
                    "name": "sequence_count",
                    "priority": 5,
                    "params": {
                        "min_sequence_length": 3,
                    },
                },
            ]
        },
        "base_signals_focused": {
            "strategies": [
                {
                    "name": "base_signals_burst",
                    "priority": 1,
                    "params": {
                        "window_ms": 150.0,  # Увеличенное окно для специализированного анализа
                        "min_cluster_size": 1,  # Даже одиночные операции
                        "include_noise": True,
                        "max_cluster_duration_ms": 10000,
                    },
                },
            ]
        },
        "enhanced_clustering": {
            "strategies": [
                {
                    "name": "time_window",
                    "priority": 1,
                    "params": {
                        "window_ms": 50,
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
                        "window_ms": 100,
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
                    strategy = strategy_class(config)
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
        return self.PRESET_CONFIGS.get(preset_name) @ classmethod

    def create_base_signals_detector(
        cls, window_ms: float = 100.0, min_cluster_size: int = 2, include_noise: bool = True
    ) -> MetaOperationDetector:
        """
        Create a detector focused on base_signals operations analysis.

        Args:
            window_ms: Temporal clustering window
            min_cluster_size: Minimum number of base_signals operations in cluster
            include_noise: Whether to include intermediate operations

        Returns:
            MetaOperationDetector: Configured detector
        """
        config = {
            "enabled": True,
            "strategies": {
                "base_signals_burst": {
                    "enabled": True,
                    "config": {
                        "window_ms": window_ms,
                        "min_cluster_size": min_cluster_size,
                        "include_noise": include_noise,
                        "max_cluster_duration_ms": 5000,
                        "priority": 1,
                    },
                }
            },
        }

        config_instance = cls()
        config_instance.load_from_dict(config)
        return config_instance.create_detector()

    @classmethod
    def create_hybrid_detector(cls) -> MetaOperationDetector:
        """
        Create a detector with combination of base_signals and general strategies.

        Returns:
            MetaOperationDetector: Hybrid detector
        """
        config_instance = cls()
        config_instance.apply_preset_config("comprehensive")
        return config_instance.create_detector()


# Create a global configuration instance
DEFAULT_META_OPERATION_CONFIG = MetaOperationConfig()

# Configure with reasonable defaults
DEFAULT_META_OPERATION_CONFIG.enable_strategy("time_window", {"window_ms": 50.0})
DEFAULT_META_OPERATION_CONFIG.enable_strategy("target_cluster", {"min_cluster_size": 3})


def get_default_detector() -> Optional[MetaOperationDetector]:
    """
    Get a detector with default configuration from logger_config.

    Returns:
        MetaOperationDetector with configured strategies or None if disabled
    """
    try:
        from ..logger_config import META_OPERATION_CONFIG

        return create_detector_from_config(META_OPERATION_CONFIG)
    except ImportError:
        # Fallback to default configuration if logger_config is not available
        return DEFAULT_META_OPERATION_CONFIG.create_detector()
    except Exception:
        # Return None if configuration fails
        return None


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


# Global configuration for meta-operations and formatting
META_OPERATION_CONFIG = {
    "enabled": True,
    "formatting": {
        "mode": "minimalist",  # Changed to "minimalist" for testing
        "header_format": "source_based",  # Changed to "source_based" for testing
        "table_format": "pipe",  # Changed to "pipe" for testing (shows | symbols)
        "show_decorative_borders": False,
        "show_completion_footer": False,
        "table_separator": "\n\n",
        "include_source_info": True,
    },
    "minimalist_settings": {
        "header_format": "source_based",
        "table_format": "pipe",  # Changed to "pipe" for testing (shows | symbols)
        "show_decorative_borders": False,
        "show_completion_footer": False,
        "table_separator": "\n\n",
        "include_source_info": True,
    },
    "strategies": {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 100.0,
            "min_cluster_size": 2,
            "include_noise": True,
            "max_cluster_duration_ms": 5000,
            "priority": 1,
        },
        "time_window": {"enabled": True, "window_ms": 50.0, "min_cluster_size": 2},
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {"enabled": True, "name_pattern": "GET_.*|SET_.*|UPDATE_.*", "min_cluster_size": 2},
        "sequence_count": {"enabled": True, "min_sequence_length": 3},
    },
}


def validate_formatting_config(config: Dict) -> Dict:
    """
    Validate formatting configuration and apply safe defaults.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Dict: Validated configuration with safe defaults
    """
    validated_config = config.copy()

    # Check mode validity
    mode = validated_config.get("mode", "standard")
    if mode not in ["standard", "minimalist"]:
        validated_config["mode"] = "standard"

    # Check table_format validity
    table_format = validated_config.get("table_format", "grid")
    valid_formats = ["grid", "simple", "plain", "fancy", "pipe", "orgtbl", "jira", "presto", "pretty", "psql", "rst"]
    if table_format not in valid_formats:
        validated_config["table_format"] = "grid"

    # Check header_format validity
    header_format = validated_config.get("header_format", "standard")
    if header_format not in ["standard", "source_based"]:
        validated_config["header_format"] = "standard"

    # Validate boolean parameters
    bool_params = ["show_decorative_borders", "show_completion_footer", "include_source_info"]
    for param in bool_params:
        if param in validated_config and not isinstance(validated_config[param], bool):
            # Try to convert to boolean
            try:
                validated_config[param] = bool(validated_config[param])
            except (ValueError, TypeError):
                # Set safe default
                if param == "show_completion_footer":
                    validated_config[param] = True  # Default to showing footer
                else:
                    validated_config[param] = False

    # Validate table_separator
    separator = validated_config.get("table_separator", "")
    if not isinstance(separator, str):
        validated_config["table_separator"] = "\n\n"

    return validated_config
