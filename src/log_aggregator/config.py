"""
Configuration module for log aggregation system.

This module provides basic configuration settings for the log aggregation
system, including buffer management and pattern detection parameters.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class AggregationConfig:
    """
    Basic configuration for log aggregation system.

    This is a minimal configuration for Stage 1 implementation.
    Advanced features like error expansion and tabular formatting
    will be added in later stages.
    """

    # Buffer management
    buffer_size: int = 100
    """Maximum number of log records to keep in buffer before processing"""

    flush_interval: float = 5.0
    """Time interval in seconds to process buffer even if not full"""

    # Pattern detection
    min_pattern_entries: int = 2
    """Minimum number of entries to consider a pattern for aggregation"""

    pattern_similarity_threshold: float = 0.8
    """Threshold for considering messages as similar (0.0 to 1.0)"""

    # Enhanced pattern detection (Stage 2)
    enhanced_patterns_enabled: bool = True
    """Whether to use enhanced pattern detection with metadata"""

    pattern_type_priorities: Dict[str, int] = None
    """Priority mapping for different pattern types (higher number = higher priority)"""

    pattern_time_windows: Dict[str, float] = None
    """Time windows in seconds for different pattern types"""

    min_cascade_depth: int = 3
    """Minimum depth for cascade pattern detection"""

    max_pattern_metadata_size: int = 1000
    """Maximum size of metadata per pattern in characters"""

    # Performance settings
    max_processing_time: float = 0.1
    """Maximum time in seconds allowed for processing one buffer flush"""

    enabled: bool = True
    """Whether aggregation is enabled"""

    # Statistics
    collect_statistics: bool = True
    """Whether to collect and log aggregation statistics"""

    def __post_init__(self):
        """Initialize default values for complex fields."""
        if self.pattern_type_priorities is None:
            self.pattern_type_priorities = {
                "plot_lines_addition": 5,
                "cascade_component_initialization": 4,
                "request_response_cycle": 3,
                "file_operations": 2,
                "gui_updates": 1,
                "basic_similarity": 0,
            }

        if self.pattern_time_windows is None:
            self.pattern_time_windows = {
                "plot_lines_addition": 2.0,
                "cascade_component_initialization": 5.0,
                "request_response_cycle": 1.0,
                "file_operations": 10.0,
                "gui_updates": 0.5,
                "basic_similarity": 5.0,
            }

    @classmethod
    def default(cls) -> "AggregationConfig":
        """Create default configuration."""
        return cls()

    @classmethod
    def minimal(cls) -> "AggregationConfig":
        """Create minimal configuration for development/testing."""
        return cls(buffer_size=20, flush_interval=2.0, min_pattern_entries=2, pattern_similarity_threshold=0.9)

    def validate(self) -> bool:
        """
        Validate configuration parameters.

        Returns:
            True if configuration is valid, False otherwise
        """
        if self.buffer_size <= 0:
            return False
        if self.flush_interval <= 0:
            return False
        if self.min_pattern_entries < 1:
            return False
        if not (0.0 <= self.pattern_similarity_threshold <= 1.0):
            return False
        if self.max_processing_time <= 0:
            return False
        if self.min_cascade_depth < 2:
            return False
        if self.max_pattern_metadata_size <= 0:
            return False

        return True
