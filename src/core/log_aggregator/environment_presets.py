"""
Configuration presets for different deployment environments.

This module provides predefined configurations for BaseSignalsBurst
and other meta-operation strategies optimized for different environments.
"""

from typing import Any, Dict

# Development configuration - more aggressive detection for testing
DEVELOPMENT_PRESET = {
    "enabled": True,
    "formatting": {
        "mode": "standard",
        "header_format": "standard",
        "table_format": "grid",
        "show_decorative_borders": True,
        "show_completion_footer": True,
        "table_separator": "\n\n",
        "include_source_info": True,
        "include_performance_metrics": True,
    },
    "strategies": {
        "base_signals_burst": {
            "enabled": True,
            "priority": 1,
            "time_window_ms": 50,  # More aggressive grouping
            "min_burst_size": 2,
            "max_gap_ms": 25,
            "max_duration_ms": 5.0,
            "include_cross_target": True,
            "debug_mode": True,  # Extra logging for development
        },
        "time_window": {"enabled": True, "priority": 2, "window_ms": 30.0, "min_cluster_size": 2},
        "target_cluster": {"enabled": True, "priority": 3, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "priority": 4,
            "name_pattern": "GET_.*|SET_.*|UPDATE_.*|LOAD_.*|SAVE_.*",
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": True, "priority": 5, "min_sequence_length": 2},
    },
}

# Production configuration - conservative settings for stability
PRODUCTION_PRESET = {
    "enabled": True,
    "formatting": {
        "mode": "minimalist",
        "header_format": "source_based",
        "table_format": "pipe",
        "show_decorative_borders": False,
        "show_completion_footer": False,
        "table_separator": "\n\n",
        "include_source_info": True,
        "include_performance_metrics": False,  # Reduced overhead
    },
    "strategies": {
        "base_signals_burst": {
            "enabled": True,
            "priority": 1,
            "time_window_ms": 100,  # Conservative timing
            "min_burst_size": 3,  # Larger minimum clusters
            "max_gap_ms": 50,
            "max_duration_ms": 10.0,
            "include_cross_target": True,
            "debug_mode": False,
        },
        "time_window": {"enabled": True, "priority": 2, "window_ms": 75.0, "min_cluster_size": 3},
        "target_cluster": {"enabled": True, "priority": 3, "min_cluster_size": 3},
        "name_similarity": {
            "enabled": False,  # Disabled for performance
            "priority": 4,
            "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
            "min_cluster_size": 3,
        },
        "sequence_count": {
            "enabled": False,  # Disabled for performance
            "priority": 5,
            "min_sequence_length": 4,
        },
    },
}

# Testing configuration - focused on BaseSignalsBurst only
TESTING_PRESET = {
    "enabled": True,
    "formatting": {
        "mode": "minimalist",
        "header_format": "source_based",
        "table_format": "simple",
        "show_decorative_borders": False,
        "show_completion_footer": False,
        "table_separator": "\n",
        "include_source_info": False,
        "include_performance_metrics": True,
    },
    "strategies": {
        "base_signals_burst": {
            "enabled": True,
            "priority": 1,
            "time_window_ms": 100,
            "min_burst_size": 2,
            "max_gap_ms": 50,
            "max_duration_ms": 10.0,
            "include_cross_target": True,
            "debug_mode": True,
        },
        "time_window": {
            "enabled": False,  # Only BaseSignals for isolated testing
            "priority": 2,
            "window_ms": 50.0,
            "min_cluster_size": 2,
        },
        "target_cluster": {"enabled": False, "priority": 3, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": False,
            "priority": 4,
            "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": False, "priority": 5, "min_sequence_length": 3},
    },
}

# Backward compatibility preset - BaseSignalsBurst disabled by default
BACKWARD_COMPATIBILITY_PRESET = {
    "enabled": True,
    "formatting": {
        "mode": "standard",
        "header_format": "standard",
        "table_format": "grid",
        "show_decorative_borders": True,
        "show_completion_footer": True,
        "table_separator": "\n\n",
        "include_source_info": True,
        "include_performance_metrics": False,
    },
    "strategies": {
        "base_signals_burst": {
            "enabled": False,  # Disabled for backward compatibility
            "priority": 1,
            "time_window_ms": 100,
            "min_burst_size": 2,
            "max_gap_ms": 50,
            "max_duration_ms": 10.0,
            "include_cross_target": True,
        },
        "time_window": {"enabled": True, "priority": 2, "window_ms": 50.0, "min_cluster_size": 2},
        "target_cluster": {"enabled": True, "priority": 3, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "priority": 4,
            "name_pattern": "GET_.*|SET_.*|UPDATE_.*",
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": True, "priority": 5, "min_sequence_length": 3},
    },
}


def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get a configuration preset by name.

    Args:
        preset_name: Name of the preset ('development', 'production', 'testing', 'backward_compatibility')

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If preset name is unknown
    """
    presets = {
        "development": DEVELOPMENT_PRESET,
        "production": PRODUCTION_PRESET,
        "testing": TESTING_PRESET,
        "backward_compatibility": BACKWARD_COMPATIBILITY_PRESET,
    }

    if preset_name not in presets:
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {list(presets.keys())}")

    return presets[preset_name].copy()


def get_available_presets():
    """Get list of available preset names."""
    return ["development", "production", "testing", "backward_compatibility"]


def apply_preset_to_config(config_manager, preset_name: str):
    """
    Apply a preset configuration to a MetaOperationConfig instance.

    Args:
        config_manager: MetaOperationConfig instance
        preset_name: Name of the preset to apply
    """
    preset_config = get_preset_config(preset_name)
    config_manager.load_from_dict(preset_config)


# Environment detection helper
def get_environment_preset() -> str:
    """
    Detect current environment and return appropriate preset name.

    Returns:
        Preset name based on environment detection
    """
    import os

    # Check environment variables
    env = os.getenv("SSK_ENVIRONMENT", "").lower()
    if env in ["dev", "development"]:
        return "development"
    elif env in ["prod", "production"]:
        return "production"
    elif env in ["test", "testing"]:
        return "testing"

    # Check if running in a testing framework
    if "pytest" in os.getenv("_", ""):
        return "testing"

    # Default to development for safety
    return "development"
