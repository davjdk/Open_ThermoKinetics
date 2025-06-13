"""
Value aggregator module for log aggregation system.

This module provides value compression and expansion for log records,
collapsing large data structures while maintaining full context for error scenarios.
"""

import re
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

try:
    from src.core.logger_config import LoggerManager
except ImportError:
    from core.logger_config import LoggerManager

from .buffer_manager import BufferedLogRecord


@dataclass
class ValueSummary:
    """Summary representation of a compressed value."""

    original_length: int
    """Original length of the data structure"""

    data_type: str
    """Type of the data structure (array, dataframe, dict, string)"""

    shape: Optional[Tuple[int, ...]]
    """Shape for multidimensional data"""

    preview: str
    """Brief preview of the data"""

    full_content: str
    """Complete original content for error context"""


@dataclass
class ValueAggregationConfig:
    """Configuration for value aggregation."""

    enabled: bool = True
    """Whether value aggregation is enabled"""

    array_threshold: int = 10
    """Minimum array size to trigger compression"""

    dataframe_threshold: int = 5
    """Minimum dataframe size to trigger compression"""

    dict_threshold: int = 8
    """Minimum dict size to trigger compression"""

    string_threshold: int = 200
    """Minimum string length to trigger compression"""

    cache_size_limit: int = 100
    """Maximum number of compressed values to cache"""


class ValueAggregator:
    """
    Aggregates and compresses large values in log messages.

    Detects large data structures and replaces them with compact
    summaries while caching full content for error contexts.
    """

    def __init__(self, config: Optional[ValueAggregationConfig] = None):
        """
        Initialize value aggregator.

        Args:
            config: Configuration for aggregation behavior
        """
        self.config = config or ValueAggregationConfig()
        self._lock = threading.RLock()

        # Cache for full content recovery
        self._value_cache: Dict[str, ValueSummary] = {}
        self._cache_order: List[str] = []

        # Statistics
        self.stats = {
            "values_compressed": 0,
            "cache_hits_on_errors": 0,
            "compression_ratio_values": 0.0,
            "cached_values": 0,
        }

        # Patterns for detecting various data types
        self.patterns = {
            "numpy_array": re.compile(r"array\(\[([\d\.,\s\-e]+)\]\)"),
            "dataframe": re.compile(r"(temperature|rate_\d+).*?\[(\d+) rows x (\d+) columns\]"),
            "coeffs_dict": re.compile(r"\"coeffs\": \{([^}]+)\}"),
            "bounds_dict": re.compile(r"\"(upper_bound_coeffs|lower_bound_coeffs)\": \{([^}]+)\}"),
            "request_dict": re.compile(r"emitting request: (\{.+\})"),
            "long_string": re.compile(rf"\"([^\"]{{{self.config.string_threshold},}})\""),
        }

        self._logger = LoggerManager.get_logger("log_aggregator.value_aggregator")

    def process_message(self, record: BufferedLogRecord) -> str:
        """
        Process log message and compress large values.

        Args:
            record: Log record to process

        Returns:
            Processed message with compressed values
        """
        with self._lock:
            message = record.record.getMessage()
            original_message = message

            # Process different types of values
            message = self._process_numpy_arrays(message, record)
            message = self._process_dataframes(message, record)
            message = self._process_dicts(message, record)
            message = self._process_long_strings(message, record)

            # Update statistics if compression occurred
            if message != original_message:
                self.stats["values_compressed"] += 1
                self._update_compression_ratio()

            return message

    def _process_numpy_arrays(self, message: str, record: BufferedLogRecord) -> str:
        """Process NumPy arrays in the message."""
        if not HAS_NUMPY:
            return message

        def replace_array(match):
            array_content = match.group(1)
            elements = array_content.split(",")

            if len(elements) < self.config.array_threshold:
                return match.group(0)  # Don"t compress small arrays

            # Create summary
            preview = f"{elements[0].strip()}, {elements[1].strip()}, {elements[2].strip()},\
                ..., {elements[-2].strip()}, {elements[-1].strip()}"
            cache_key = self._generate_cache_key(record)

            summary = ValueSummary(
                original_length=len(elements),
                data_type="numpy.ndarray",
                shape=(len(elements),),
                preview=preview,
                full_content=match.group(0),
            )

            self._add_to_cache(cache_key, summary)

            return f"📊 array({len(elements)} elements) [{preview}]"

        return self.patterns["numpy_array"].sub(replace_array, message)

    def _process_dataframes(self, message: str, record: BufferedLogRecord) -> str:
        """Process pandas DataFrames in the message."""
        if not HAS_PANDAS:
            return message

        def replace_dataframe(match):
            column_name = match.group(1)
            rows = int(match.group(2))
            cols = int(match.group(3))

            if rows < self.config.dataframe_threshold:
                return match.group(0)  # Don"t compress small dataframes

            cache_key = self._generate_cache_key(record)

            summary = ValueSummary(
                original_length=rows * cols,
                data_type="pandas.DataFrame",
                shape=(rows, cols),
                preview=f"{column_name} ({rows}×{cols})",
                full_content=match.group(0),
            )

            self._add_to_cache(cache_key, summary)

            return f"📊 DataFrame({rows}×{cols}) [{column_name} ({rows}×{cols})]"

        return self.patterns["dataframe"].sub(replace_dataframe, message)

    def _process_dicts(self, message: str, record: BufferedLogRecord) -> str:
        """Process dictionaries in the message."""

        def replace_dict(match, dict_type="dict"):
            dict_content = match.group(1) if dict_type == "coeffs" else match.group(2)

            # Count items by splitting on commas (rough estimate)
            items = [item.strip() for item in dict_content.split(",") if item.strip()]

            if len(items) < self.config.dict_threshold:
                return match.group(0)  # Don"t compress small dicts

            # Create preview with first and last items
            if len(items) >= 2:
                preview = f"{items[0]}, ..., {items[-1]}"
            else:
                preview = items[0] if items else "empty"

            cache_key = self._generate_cache_key(record)

            summary = ValueSummary(
                original_length=len(items),
                data_type=f"dict[{dict_type}]",
                shape=None,
                preview=preview,
                full_content=match.group(0),
            )

            self._add_to_cache(cache_key, summary)

            return f"📊 {dict_type}({len(items)} items) [{preview}]"

        # Process coefficients dictionaries
        message = self.patterns["coeffs_dict"].sub(lambda m: replace_dict(m, "coeffs"), message)

        # Process bounds dictionaries
        message = self.patterns["bounds_dict"].sub(lambda m: replace_dict(m, "bounds"), message)

        # Process request dictionaries
        message = self.patterns["request_dict"].sub(lambda m: replace_dict(m, "request"), message)

        return message

    def _process_long_strings(self, message: str, record: BufferedLogRecord) -> str:
        """Process long strings in the message."""

        def replace_string(match):
            content = match.group(1)

            if len(content) < self.config.string_threshold:
                return match.group(0)  # Don"t compress short strings

            # Create preview with beginning and end
            preview = f"{content[:50]}...{content[-50:]}"
            cache_key = self._generate_cache_key(record)

            summary = ValueSummary(
                original_length=len(content),
                data_type="string",
                shape=None,
                preview=preview,
                full_content=match.group(0),
            )

            self._add_to_cache(cache_key, summary)

            return f'📊 string({len(content)} chars) ["{preview}"]'

        return self.patterns["long_string"].sub(replace_string, message)

    def _generate_cache_key(self, record: BufferedLogRecord) -> str:
        """Generate unique cache key for the record."""
        return f"{record.timestamp.isoformat()}_{id(record)}"

    def _add_to_cache(self, key: str, summary: ValueSummary) -> None:
        """Add summary to cache with size limit management."""
        # Remove oldest entries if cache is full
        while len(self._value_cache) >= self.config.cache_size_limit:
            oldest_key = self._cache_order.pop(0)
            del self._value_cache[oldest_key]

        self._value_cache[key] = summary
        self._cache_order.append(key)
        self.stats["cached_values"] = len(self._value_cache)

    def get_full_context(self, record: BufferedLogRecord) -> Optional[str]:
        """
        Get full context for error records.

        Args:
            record: Log record that may need full context

        Returns:
            Full message with expanded values if available
        """
        with self._lock:
            cache_key = self._generate_cache_key(record)

            if cache_key in self._value_cache:
                self.stats["cache_hits_on_errors"] += 1
                summary = self._value_cache[cache_key]
                return summary.full_content

            return None

    def _update_compression_ratio(self) -> None:
        """Update compression ratio statistics."""
        # Simple ratio based on compressed vs total processed
        # More sophisticated calculation could be implemented
        self.stats["compression_ratio_values"] = min(
            0.99, self.stats["values_compressed"] / max(1, self.stats["values_compressed"] + 100)
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregation statistics."""
        with self._lock:
            # Update cached_values count before returning stats
            current_stats = self.stats.copy()
            current_stats["cached_values"] = len(self._value_cache)
            return current_stats

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self.stats = {
                "values_compressed": 0,
                "cache_hits_on_errors": 0,
                "compression_ratio_values": 0.0,
                "cached_values": len(self._value_cache),
            }

    def clear_cache(self) -> None:
        """Clear the value cache."""
        with self._lock:
            self._value_cache.clear()
            self._cache_order.clear()
            self.stats["cached_values"] = 0
