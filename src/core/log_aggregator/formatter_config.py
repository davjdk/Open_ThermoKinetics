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
    indent_size: int = 2  # Indent size for nested operations    # Additional meta-operations options
    show_meta_statistics: bool = True  # Show statistics for groups
    highlight_errors: bool = True  # Highlight errors in groups
    time_precision: int = 3  # Time precision (decimal places)

    # BaseSignalsMetaBurst specific configuration
    base_signals_burst: Dict[str, Any] = None

    # Output modes configuration
    output_modes: Dict[str, str] = None  # Display filters
    display_filters: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values for complex fields."""
        if self.base_signals_burst is None:
            self.base_signals_burst = {
                "show_in_table": True,  # Show in main table
                "collapsed_by_default": True,  # Collapsed display by default
                "show_noise_markers": True,  # Mark noise operations
                "noise_marker": "[*]",  # Marker for noise operations
                "show_detailed_summary": True,  # Detailed cluster summary
                "group_header_style": "enhanced",  # Group header style
                "indent_sub_operations": True,  # Indent for sub-operations
            }

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


# Noise marker styles for BaseSignalsMetaBurst
NOISE_MARKER_STYLES = {
    "asterisk": "[*]",
    "warning": "[!]",
    "tilde": "[~]",
    "arrow": "[→]",
    "dot": "[·]",
    "hash": "[#]",
}


# Mode-specific configurations
MODE_CONFIGS = {
    "compact": {
        "compact_meta_view": True,
        "show_individual_ops": False,
        "meta_operation_symbol": "►",
        "show_meta_statistics": False,
        "base_signals_burst": {
            "collapsed_by_default": True,
            "show_noise_markers": False,
            "show_detailed_summary": False,
        },
    },
    "expanded": {
        "compact_meta_view": False,
        "show_individual_ops": True,
        "meta_operation_symbol": "◣",
        "show_meta_statistics": True,
        "base_signals_burst": {
            "collapsed_by_default": False,
            "show_noise_markers": True,
            "show_detailed_summary": True,
        },
    },
    "debug": {
        "compact_meta_view": False,
        "show_individual_ops": True,
        "show_meta_statistics": True,
        "highlight_errors": True,
        "time_precision": 6,
        "base_signals_burst": {
            "collapsed_by_default": False,
            "show_noise_markers": True,
            "show_detailed_summary": True,
            "use_color": True,
            "noise_marker_style": "warning",
        },
    },
    "minimal": {
        "group_meta_operations": True,
        "compact_meta_view": True,
        "show_individual_ops": False,
        "show_meta_statistics": False,
        "max_cell_width": 30,
        "base_signals_burst": {
            "collapsed_by_default": True,
            "show_noise_markers": False,
            "show_detailed_summary": False,
        },
    },
}


# Extended configuration with meta-operation display settings
DEFAULT_FORMATTING_CONFIG = {
    "meta_operation_display": {
        "show_cluster_boundaries": True,  # Show cluster boundaries
        "highlight_base_signals": True,  # Highlight base_signals operations
        "summary_position": "after_operations",  # Summary position (before/after/both)
    },
    "base_signals_burst": {
        "show_in_table": True,  # Show in main table
        "collapsed_by_default": True,  # Collapsed display by default
        "show_noise_markers": True,  # Mark noise operations
        "noise_marker": "[*]",  # Marker for noise operations
        "noise_marker_style": "asterisk",  # Style from NOISE_MARKER_STYLES
        "show_detailed_summary": True,  # Detailed cluster summary
        "group_header_style": "enhanced",  # Group header style
        "indent_sub_operations": True,  # Indent for sub-operations
        "use_color": False,  # Use color styling if supported
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
            if key == "base_signals_burst":
                # Special handling for nested base_signals_burst config
                if hasattr(base_config, "base_signals_burst") and base_config.base_signals_burst:
                    base_config.base_signals_burst.update(value)
                else:
                    base_config.base_signals_burst = value.copy()
            elif hasattr(base_config, key):
                setattr(base_config, key, value)

    return base_config
