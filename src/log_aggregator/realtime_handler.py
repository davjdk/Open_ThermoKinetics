"""
Real-time handler module for log aggregation system.

This module provides the main AggregatingHandler class that integrates
with Python's logging system to provide real-time log aggregation.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

from src.core.logger_config import LoggerManager

from .aggregation_engine import AggregationEngine
from .buffer_manager import BufferManager
from .config import AggregationConfig
from .pattern_detector import PatternDetector


class AggregatingHandler(logging.Handler):
    """
    Custom logging handler that provides real-time log aggregation.

    This handler buffers log records, detects patterns, and outputs
    aggregated summaries while maintaining compatibility with existing
    logging infrastructure.
    """

    def __init__(self, target_handler: Optional[logging.Handler] = None, config: Optional[AggregationConfig] = None):
        """
        Initialize aggregating handler.

        Args:
            target_handler: Handler to forward aggregated records to
            config: Configuration for aggregation behavior
        """
        super().__init__()

        self.config = config or AggregationConfig.default()
        self.target_handler = target_handler

        # Initialize components
        self.buffer_manager = BufferManager(max_size=self.config.buffer_size, flush_interval=self.config.flush_interval)

        self.pattern_detector = PatternDetector(similarity_threshold=self.config.pattern_similarity_threshold)

        self.aggregation_engine = AggregationEngine(min_pattern_entries=self.config.min_pattern_entries)

        # Processing control
        self._processing_lock = threading.RLock()
        self._last_process_time = time.time()
        self._enabled = self.config.enabled

        # Statistics
        self._total_records_received = 0
        self._total_records_forwarded = 0
        self._total_processing_runs = 0
        self._total_processing_time = 0.0

        # Logger for internal messages
        self._logger = LoggerManager.get_logger("log_aggregator.realtime_handler")

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.

        Args:
            record: LogRecord to process
        """
        try:
            self._total_records_received += 1

            # Always forward to target handler if aggregation is disabled
            if not self._enabled:
                self._forward_to_target(record)
                return

            # Add record to buffer
            self.buffer_manager.add_record(record)

            # Check if we should process the buffer
            if self.buffer_manager.should_process():
                self._process_buffer()

            # For Stage 1, also forward original record to maintain compatibility
            # In later stages, this might be configurable
            self._forward_to_target(record)

        except Exception as e:
            self._logger.error(f"Error in AggregatingHandler.emit: {e}")
            # Fallback: forward original record
            self._forward_to_target(record)

    def _process_buffer(self) -> None:
        """Process buffered records and emit aggregated summaries."""
        with self._processing_lock:
            start_time = time.time()

            try:
                # Get records for processing
                records = self.buffer_manager.get_records_for_processing()
                if not records:
                    return

                # Detect patterns
                patterns = self.pattern_detector.detect_patterns(records)

                # Create aggregated records
                aggregated_records = self.aggregation_engine.process_records(records, patterns)

                # Emit aggregated summaries
                for aggregated in aggregated_records:
                    self._emit_aggregated_record(aggregated)

                # Update statistics
                self._total_processing_runs += 1
                processing_time = time.time() - start_time
                self._total_processing_time += processing_time

                if self.config.collect_statistics:
                    self._log_processing_statistics(
                        len(records), len(patterns), len(aggregated_records), processing_time
                    )

            except Exception as e:
                self._logger.error(f"Error processing buffer: {e}")

            finally:
                self._last_process_time = time.time()

    def _emit_aggregated_record(self, aggregated_record) -> None:
        """Emit an aggregated record as a log message."""
        try:
            # Create a log record for the aggregated summary
            log_record = logging.LogRecord(
                name=f"aggregator.{aggregated_record.logger_name}",
                level=getattr(logging, aggregated_record.level),
                pathname="",
                lineno=0,
                msg=aggregated_record.to_log_message(),
                args=(),
                exc_info=None,
            )

            # Forward to target handler
            self._forward_to_target(log_record)

        except Exception as e:
            self._logger.error(f"Error emitting aggregated record: {e}")

    def _forward_to_target(self, record: logging.LogRecord) -> None:
        """Forward a record to the target handler."""
        if self.target_handler:
            try:
                self.target_handler.emit(record)
                self._total_records_forwarded += 1
            except Exception as e:
                self._logger.error(f"Error forwarding to target handler: {e}")

    def _log_processing_statistics(
        self, records_count: int, patterns_count: int, aggregated_count: int, processing_time: float
    ) -> None:
        """Log processing statistics."""
        self._logger.debug(
            f"Processed {records_count} records, found {patterns_count} patterns, "
            f"created {aggregated_count} aggregations in {processing_time:.3f}s"
        )

    def flush(self) -> None:
        """Flush any buffered records."""
        if self._enabled:
            self._process_buffer()

        if self.target_handler:
            self.target_handler.flush()

    def close(self) -> None:
        """Close the handler and clean up resources."""
        try:
            # Process any remaining buffered records
            self.flush()

            # Close target handler
            if self.target_handler:
                self.target_handler.close()

        finally:
            super().close()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable aggregation."""
        self._enabled = enabled
        if enabled:
            self._logger.info("Log aggregation enabled")
        else:
            self._logger.info("Log aggregation disabled")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about aggregation performance."""
        buffer_stats = self.buffer_manager.get_statistics()
        pattern_stats = self.pattern_detector.get_pattern_statistics()
        aggregation_stats = self.aggregation_engine.get_statistics()

        return {
            "handler": {
                "total_records_received": self._total_records_received,
                "total_records_forwarded": self._total_records_forwarded,
                "total_processing_runs": self._total_processing_runs,
                "total_processing_time": self._total_processing_time,
                "average_processing_time": (
                    self._total_processing_time / self._total_processing_runs if self._total_processing_runs > 0 else 0
                ),
                "enabled": self._enabled,
            },
            "buffer": buffer_stats,
            "patterns": pattern_stats,
            "aggregation": aggregation_stats,
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._total_records_received = 0
        self._total_records_forwarded = 0
        self._total_processing_runs = 0
        self._total_processing_time = 0.0

        self.buffer_manager.reset_statistics()
        self.pattern_detector.clear_patterns()
        self.aggregation_engine.reset_statistics()
