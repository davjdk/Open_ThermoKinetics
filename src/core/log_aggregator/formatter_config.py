"""
Configuration module for operation table formatter with meta-operations support.

This module provides comprehensive configuration for the enhanced OperationTableFormatter
with support for meta-operations visualization, grouping, and display customization.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class FormatterConfig:
    """
    Configuration for OperationTableFormatter with meta-operations support.

    This dataclass provides all formatting options including meta-operations
    grouping, display modes, and visualization parameters.
    """

    # Basic table formatting parameters
    table_format: str = "grid"
    max_cell_width: int = 50
    include_error_details: bool = True
    max_error_context_items: int = 5

    # Meta-operations formatting parameters
    group_meta_operations: bool = True  # Enable grouping in output
    compact_meta_view: bool = True  # Compact display of groups
    show_individual_ops: bool = False  # Show individual operations within groups
    max_operations_inline: int = 5  # Maximum operations for inline display
    meta_operation_symbol: str = "►"  # Symbol for meta-operations
    indent_size: int = 2  # Indent size for nested operations

    # Additional meta-operations options
    show_meta_statistics: bool = True  # Show statistics for groups
    highlight_errors: bool = True  # Highlight errors in groups
    time_precision: int = 3  # Time precision (decimal places)

    # Output modes configuration
    output_modes: Dict[str, str] = None

    # Display filters
    display_filters: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values for complex fields."""
        if self.output_modes is None:
            self.output_modes = {
                "default": "compact",  # Default mode
                "debug": "expanded",  # Debug mode
                "json": False,  # Additional JSON output
            }

        if self.display_filters is None:
            self.display_filters = {
                "min_group_size": 2,  # Minimum group size for display
                "max_group_size": 50,  # Maximum size for expanded display
                "hide_successful_groups": False,  # Hide fully successful groups
                "hide_single_operations": False,  # Hide single operations
            }


# Mode-specific configurations
MODE_CONFIGS = {
    "compact": {
        "compact_meta_view": True,
        "show_individual_ops": False,
        "meta_operation_symbol": "►",
        "show_meta_statistics": False,
    },
    "expanded": {
        "compact_meta_view": False,
        "show_individual_ops": True,
        "meta_operation_symbol": "◣",
        "show_meta_statistics": True,
    },
    "debug": {
        "compact_meta_view": False,
        "show_individual_ops": True,
        "show_meta_statistics": True,
        "highlight_errors": True,
        "time_precision": 6,
    },
    "minimal": {
        "group_meta_operations": True,
        "compact_meta_view": True,
        "show_individual_ops": False,
        "show_meta_statistics": False,
        "max_cell_width": 30,
    },
}


def create_config_for_mode(mode: str) -> FormatterConfig:
    """
    Create FormatterConfig for specific output mode.

    Args:
        mode: Output mode name (compact, expanded, debug, minimal)

    Returns:
        FormatterConfig: Configured instance for the specified mode
    """
    base_config = FormatterConfig()

    if mode in MODE_CONFIGS:
        mode_settings = MODE_CONFIGS[mode]
        for key, value in mode_settings.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)

    return base_config
