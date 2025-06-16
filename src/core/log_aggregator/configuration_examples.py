"""
Configuration examples for meta-operation clustering.

This module provides practical configuration examples for different use cases
and scenarios in the solid-state kinetics application.
"""

# Example 1: Conservative configuration for production
PRODUCTION_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "time_window_ms": 25,  # Tight window for precise grouping
            "min_cluster_size": 3,  # Only group significant clusters
        },
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": False,  # Disabled to avoid false positives
            "name_pattern": r"(GET_|SET_|UPDATE_).*",
            "min_cluster_size": 2,
        },
        "sequence_count": {
            "enabled": False,  # Disabled for safety
            "min_sequence_count": 5,
            "min_cluster_size": 5,
        },
    },
    "formatting": {"mode": "compact", "show_individual_operations": True, "meta_operation_summary": True},
}

# Example 2: Aggressive configuration for analysis and optimization
ANALYSIS_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "time_window_ms": 100,  # Wider window for more grouping
            "min_cluster_size": 2,  # Lower threshold
        },
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"(GET_|SET_|UPDATE_|LOAD_|SAVE_).*",
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": True, "min_sequence_count": 3, "min_cluster_size": 3},
    },
    "formatting": {
        "mode": "detailed",  # Full details for analysis
        "show_individual_operations": True,
        "meta_operation_summary": True,
    },
}

# Example 3: Performance-focused configuration
PERFORMANCE_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {"enabled": True, "time_window_ms": 50, "min_cluster_size": 2},
        "target_cluster": {
            "enabled": False,  # Disabled for performance
            "min_cluster_size": 2,
        },
        "name_similarity": {
            "enabled": False,  # Regex can be expensive
            "name_pattern": r".*",
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": False, "min_sequence_count": 3, "min_cluster_size": 3},
    },
    "formatting": {
        "mode": "compact",
        "show_individual_operations": False,  # Minimal output
        "meta_operation_summary": True,
    },
}

# Example 4: Debug configuration for development
DEBUG_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "time_window_ms": 200,  # Very wide window for testing
            "min_cluster_size": 1,  # Group everything possible
        },
        "target_cluster": {"enabled": True, "min_cluster_size": 1},
        "name_similarity": {
            "enabled": True,
            "name_pattern": r".*",  # Match everything
            "min_cluster_size": 1,
        },
        "sequence_count": {
            "enabled": True,
            "min_sequence_count": 2,  # Very low threshold
            "min_cluster_size": 2,
        },
    },
    "formatting": {"mode": "detailed", "show_individual_operations": True, "meta_operation_summary": True},
}

# Example 5: Specific pattern configurations for different workflows

# Configuration for file operations workflow
FILE_OPERATIONS_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {"enabled": True, "time_window_ms": 50, "min_cluster_size": 2},
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"(LOAD_|SAVE_|CHECK_|GET_DF_).*",  # File-specific patterns
            "min_cluster_size": 2,
        },
        "sequence_count": {"enabled": False, "min_sequence_count": 3, "min_cluster_size": 3},
    },
    "formatting": {"mode": "compact", "show_individual_operations": True, "meta_operation_summary": True},
}

# Configuration for calculation operations workflow
CALCULATION_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "time_window_ms": 30,  # Tight grouping for calculations
            "min_cluster_size": 2,
        },
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"(SET_|UPDATE_|GET_VALUE|CALCULATE_).*",
            "min_cluster_size": 2,
        },
        "sequence_count": {
            "enabled": True,  # Important for iterative calculations
            "min_sequence_count": 3,
            "min_cluster_size": 3,
        },
    },
    "formatting": {
        "mode": "table",  # Good for calculation analysis
        "show_individual_operations": True,
        "meta_operation_summary": True,
    },
}

# Configuration for model-based analysis workflow
MODEL_BASED_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {
            "enabled": True,
            "time_window_ms": 100,  # Wider window for complex operations
            "min_cluster_size": 2,
        },
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {
            "enabled": True,
            "name_pattern": r"(MODEL_|SCHEME_|PARAM_|OPTIMIZE_).*",
            "min_cluster_size": 2,
        },
        "sequence_count": {
            "enabled": True,
            "min_sequence_count": 5,  # Longer sequences in optimization
            "min_cluster_size": 5,
        },
    },
    "formatting": {"mode": "detailed", "show_individual_operations": True, "meta_operation_summary": True},
}

# Example 6: Minimal configuration for basic clustering
MINIMAL_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {"enabled": True, "time_window_ms": 50, "min_cluster_size": 2},
        "target_cluster": {"enabled": False, "min_cluster_size": 2},
        "name_similarity": {"enabled": False, "name_pattern": r".*", "min_cluster_size": 2},
        "sequence_count": {"enabled": False, "min_sequence_count": 3, "min_cluster_size": 3},
    },
    "formatting": {"mode": "compact", "show_individual_operations": False, "meta_operation_summary": False},
}

# Example 7: JSON output configuration for automated analysis
JSON_OUTPUT_CONFIG = {
    "enabled": True,
    "strategies": {
        "time_window": {"enabled": True, "time_window_ms": 50, "min_cluster_size": 2},
        "target_cluster": {"enabled": True, "min_cluster_size": 2},
        "name_similarity": {"enabled": True, "name_pattern": r"(GET_|SET_|UPDATE_).*", "min_cluster_size": 2},
        "sequence_count": {"enabled": True, "min_sequence_count": 3, "min_cluster_size": 3},
    },
    "formatting": {
        "mode": "json",  # Machine-readable output
        "show_individual_operations": True,
        "meta_operation_summary": True,
    },
}


# Helper function to apply configuration
def apply_meta_operation_config(config_name: str):
    """
    Apply a predefined meta-operation configuration.

    Args:
        config_name: Name of the configuration to apply
                    Options: "production", "analysis", "performance", "debug",
                            "file_ops", "calculation", "model_based", "minimal", "json"

    Example:
        apply_meta_operation_config("production")
    """
    configs = {
        "production": PRODUCTION_CONFIG,
        "analysis": ANALYSIS_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "debug": DEBUG_CONFIG,
        "file_ops": FILE_OPERATIONS_CONFIG,
        "calculation": CALCULATION_CONFIG,
        "model_based": MODEL_BASED_CONFIG,
        "minimal": MINIMAL_CONFIG,
        "json": JSON_OUTPUT_CONFIG,
    }

    if config_name not in configs:
        raise ValueError(f"Unknown config: {config_name}. Available: {list(configs.keys())}")

    # In a real implementation, this would update the actual configuration
    # For now, return the configuration for manual application
    return configs[config_name]


# Example usage patterns
def get_config_for_workflow(workflow_type: str, performance_priority: bool = False):
    """
    Get recommended configuration based on workflow type and performance requirements.

    Args:
        workflow_type: Type of workflow ("file_processing", "calculations", "model_based", "general")
        performance_priority: Whether to prioritize performance over detailed clustering

    Returns:
        Configuration dictionary
    """
    if performance_priority:
        return PERFORMANCE_CONFIG

    workflow_configs = {
        "file_processing": FILE_OPERATIONS_CONFIG,
        "calculations": CALCULATION_CONFIG,
        "model_based": MODEL_BASED_CONFIG,
        "general": PRODUCTION_CONFIG,
    }

    return workflow_configs.get(workflow_type, PRODUCTION_CONFIG)


# Configuration validation helper
def validate_config(config: dict) -> list:
    """
    Validate meta-operation configuration and return list of issues.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    if not isinstance(config.get("enabled"), bool):
        issues.append("'enabled' must be a boolean")

    strategies = config.get("strategies", {})
    for strategy_name, strategy_config in strategies.items():
        if not isinstance(strategy_config.get("enabled"), bool):
            issues.append(f"strategies.{strategy_name}.enabled must be a boolean")

        if "min_cluster_size" in strategy_config:
            if not isinstance(strategy_config["min_cluster_size"], int) or strategy_config["min_cluster_size"] < 1:
                issues.append(f"strategies.{strategy_name}.min_cluster_size must be a positive integer")

    # Validate time window specific settings
    if "time_window" in strategies:
        time_config = strategies["time_window"]
        if "time_window_ms" in time_config:
            if not isinstance(time_config["time_window_ms"], (int, float)) or time_config["time_window_ms"] <= 0:
                issues.append("strategies.time_window.time_window_ms must be a positive number")

    # Validate formatting settings
    formatting = config.get("formatting", {})
    valid_modes = {"compact", "detailed", "table", "json"}
    if "mode" in formatting and formatting["mode"] not in valid_modes:
        issues.append(f"formatting.mode must be one of {valid_modes}")

    return issues


# Example configuration testing
if __name__ == "__main__":
    # Test all configurations
    configs_to_test = [
        ("Production", PRODUCTION_CONFIG),
        ("Analysis", ANALYSIS_CONFIG),
        ("Performance", PERFORMANCE_CONFIG),
        ("Debug", DEBUG_CONFIG),
        ("File Operations", FILE_OPERATIONS_CONFIG),
        ("Calculation", CALCULATION_CONFIG),
        ("Model Based", MODEL_BASED_CONFIG),
        ("Minimal", MINIMAL_CONFIG),
        ("JSON Output", JSON_OUTPUT_CONFIG),
    ]

    print("Testing meta-operation configurations...")
    for name, config in configs_to_test:
        issues = validate_config(config)
        if issues:
            print(f"❌ {name}: {', '.join(issues)}")
        else:
            print(f"✅ {name}: Valid configuration")

    print("\nConfiguration testing completed.")
