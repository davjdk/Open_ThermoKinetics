"""
Configuration module for log aggregation system.

This module provides basic configuration settings for the log aggregation
system, including buffer management and pattern detection parameters.
"""

from dataclasses import dataclass


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

    # Performance settings
    max_processing_time: float = 0.1
    """Maximum time in seconds allowed for processing one buffer flush"""

    enabled: bool = True
    """Whether aggregation is enabled"""

    # Statistics
    collect_statistics: bool = True
    """Whether to collect and log aggregation statistics"""

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

        return True
