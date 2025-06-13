"""
Real-time handler module for log aggregation system.

This module provides the main AggregatingHandler class that integrates
with Python's logging system to provide real-time log aggregation.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

try:
    from src.core.logger_config import LoggerManager
except ImportError:
    from core.logger_config import LoggerManager

from .aggregation_engine import AggregationEngine
from .buffer_manager import BufferedLogRecord, BufferManager
from .config import AggregationConfig
from .error_expansion import ErrorExpansionConfig, ErrorExpansionEngine
from .operation_aggregator import OperationAggregationConfig, OperationAggregator
from .pattern_detector import PatternDetector
from .tabular_formatter import TabularFormatter
from .value_aggregator import ValueAggregationConfig, ValueAggregator


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

        # Tabular formatter (Stage 3)
        self.tabular_formatter = TabularFormatter(config=self.config.tabular_formatting)
        self.enable_tabular_format = self.config.tabular_formatting.enabled  # Error expansion engine (Stage 4)
        error_config = ErrorExpansionConfig(
            enabled=getattr(self.config, "error_expansion_enabled", True),
            context_lines=getattr(self.config, "error_context_lines", 5),
            trace_depth=getattr(self.config, "error_trace_depth", 10),
            immediate_expansion=getattr(self.config, "error_immediate_expansion", True),
            error_threshold_level=getattr(self.config, "error_threshold_level", "WARNING"),
            context_time_window=getattr(self.config, "error_context_time_window", 10.0),
        )
        self.error_expansion_engine = ErrorExpansionEngine(config=error_config)
        self.enable_error_expansion = error_config.enabled

        # Operation aggregator (Stage 4.5)
        operation_config = OperationAggregationConfig(
            enabled=getattr(self.config, "operation_aggregation_enabled", True),
            cascade_window=getattr(self.config, "operation_cascade_window", 1.0),
            min_cascade_size=getattr(self.config, "operation_min_cascade_size", 3),
        )
        self.operation_aggregator = OperationAggregator(config=operation_config)
        self.enable_operation_aggregation = operation_config.enabled

        # Value aggregator (Stage 4.5)
        value_config = ValueAggregationConfig(
            enabled=getattr(self.config, "value_aggregation_enabled", True),
            array_threshold=getattr(self.config, "value_array_threshold", 10),
            dataframe_threshold=getattr(self.config, "value_dataframe_threshold", 5),
            dict_threshold=getattr(self.config, "value_dict_threshold", 8),
            string_threshold=getattr(self.config, "value_string_threshold", 200),
            cache_size_limit=getattr(self.config, "value_cache_size_limit", 100),
        )
        self.value_aggregator = ValueAggregator(config=value_config)
        self.enable_value_aggregation = value_config.enabled

        # Processing control
        self._processing_lock = threading.RLock()
        self._last_process_time = time.time()
        self._enabled = self.config.enabled

        # Statistics
        self._total_records_received = 0
        self._total_records_forwarded = 0
        self._total_processing_runs = 0
        self._total_processing_time = 0.0
        self._tables_generated = 0
        self._errors_expanded = 0  # Logger for internal messages
        self._logger = LoggerManager.get_logger("log_aggregator.realtime_handler")

    def emit(self, record: logging.LogRecord) -> None:  # noqa: C901
        """
        Emit a log record with aggregation support.

        Args:
            record: LogRecord to process
        """
        try:
            self._total_records_received += 1

            # Always forward to target handler if aggregation is disabled
            if not self._enabled:
                self._forward_to_target(record)
                return  # Convert to BufferedLogRecord for processing
            from datetime import datetime

            buffered_record = BufferedLogRecord(
                record=record, timestamp=datetime.now()
            )  # Value aggregation (Stage 4.5) - apply to all non-error records
            if self.enable_value_aggregation and record.levelno < logging.WARNING:
                processed_message = self.value_aggregator.process_message(buffered_record)
                # Update the record message with the processed version
                record.msg = processed_message  # Operation aggregation (Stage 4.5) - detect operation cascades
            cascade_handled = False
            if self.enable_operation_aggregation:
                completed_group = self.operation_aggregator.process_record(buffered_record)
                if completed_group:
                    # Emit aggregated operation cascade
                    aggregated_record = self.operation_aggregator.get_aggregated_record(completed_group)
                    self._forward_to_target(aggregated_record.record)
                    return  # Don't forward individual operations

                # Check if this record is part of an ongoing cascade
                cascade_handled = self.operation_aggregator.current_group is not None

            # Add record to buffer
            self.buffer_manager.add_record(record)

            # Check for immediate error expansion (Stage 4)
            if self.enable_error_expansion:
                buffered_record = self.buffer_manager._context_buffer[-1]  # Get the just-added record
                if self.error_expansion_engine.is_error_record(buffered_record):
                    # Restore full values for error context
                    if self.enable_value_aggregation:
                        full_context = self.value_aggregator.get_full_context(buffered_record)
                        if full_context:
                            buffered_record.record.msg = full_context

                    self._handle_error_immediately(buffered_record)
                    return  # Don't forward original error, only expanded version

            # Check if we should process the buffer
            if self.buffer_manager.should_process():
                self._process_buffer()  # Forward processed record to target handler only if not part of cascade
            if not cascade_handled:
                self._forward_to_target(record)

        except Exception as e:
            self._logger.error(f"Error in AggregatingHandler.emit: {e}")
            # Fallback: forward original record
            self._forward_to_target(record)

    def _handle_error_immediately(self, error_record) -> None:
        """
        Handle error immediately with expanded context.

        Args:
            error_record: BufferedLogRecord representing the error
        """
        try:
            # Get recent context for error analysis
            context_records = self.buffer_manager.get_recent_context()

            # Expand the error with context
            expanded_record = self.error_expansion_engine.expand_error(error_record, context_records)

            # Forward expanded record to target handler
            self._forward_to_target(expanded_record.record)

            # Update statistics
            self._errors_expanded += 1

            self._logger.debug(f"Expanded error: {error_record.record.getMessage()[:100]}")

        except Exception as e:
            self._logger.error(f"Error in immediate error expansion: {e}")
            # Fallback: forward original record
            self._forward_to_target(error_record.record)

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

                # Tabular formatting (Stage 3)
                if self.enable_tabular_format and patterns:
                    table_records = self.tabular_formatter.format_patterns_as_tables(patterns)
                    aggregated_records.extend(table_records)
                    self._tables_generated += len(table_records)

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
            # Handle both AggregatedLogRecord and BufferedLogRecord (from tabular formatter)
            if hasattr(aggregated_record, "to_log_message"):
                # AggregatedLogRecord
                log_record = logging.LogRecord(
                    name=f"aggregator.{aggregated_record.logger_name}",
                    level=getattr(logging, aggregated_record.level),
                    pathname="",
                    lineno=0,
                    msg=aggregated_record.to_log_message(),
                    args=(),
                    exc_info=None,
                )
            else:
                # BufferedLogRecord (from tabular formatter)
                log_record = logging.LogRecord(
                    name=aggregated_record.logger_name,
                    level=aggregated_record.level_no,
                    pathname="",
                    lineno=0,
                    msg=aggregated_record.message,
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

    def toggle_tabular_format(self, enabled: bool) -> None:
        """Enable or disable tabular formatting."""
        self.enable_tabular_format = enabled
        self.tabular_formatter.toggle_tabular_format(enabled)
        if enabled:
            self._logger.info("Tabular formatting enabled")
        else:
            self._logger.info("Tabular formatting disabled")

    def toggle_error_expansion(self, enabled: bool) -> None:
        """Enable or disable error expansion."""
        self.enable_error_expansion = enabled
        if enabled:
            self._logger.info("Error expansion enabled")
        else:
            self._logger.info("Error expansion disabled")

    def toggle_operation_aggregation(self, enabled: bool) -> None:
        """Enable/disable operation aggregation."""
        self.enable_operation_aggregation = enabled
        self._logger.info(f"Operation aggregation {'enabled' if enabled else 'disabled'}")

    def toggle_value_aggregation(self, enabled: bool) -> None:
        """Enable/disable value aggregation."""
        self.enable_value_aggregation = enabled
        self._logger.info(f"Value aggregation {'enabled' if enabled else 'disabled'}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about aggregation performance."""
        buffer_stats = self.buffer_manager.get_statistics()
        pattern_stats = self.pattern_detector.get_pattern_statistics()
        aggregation_stats = self.aggregation_engine.get_statistics()
        error_expansion_stats = self.error_expansion_engine.get_statistics()

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
                "tables_generated": self._tables_generated,
                "tabular_formatting_enabled": self.enable_tabular_format,
                "errors_expanded": self._errors_expanded,
                "error_expansion_enabled": self.enable_error_expansion,
            },
            "buffer": buffer_stats,
            "patterns": pattern_stats,
            "aggregation": aggregation_stats,
            "error_expansion": error_expansion_stats,
        }

    def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get statistics from aggregators."""
        stats = {}

        if self.enable_operation_aggregation:
            operation_stats = self.operation_aggregator.get_stats()
            stats.update(
                {
                    "operation_cascades_aggregated": operation_stats.get("cascades_detected", 0),
                    "current_cascade_size": (
                        self.operation_aggregator.current_group.operation_count
                        if self.operation_aggregator.current_group
                        else 0
                    ),
                    "operation_compression_ratio": operation_stats.get("compression_ratio", 0.0),
                }
            )

        if self.enable_value_aggregation:
            value_stats = self.value_aggregator.get_stats()
            stats.update(value_stats)

        return stats

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._total_records_received = 0
        self._total_records_forwarded = 0
        self._total_processing_runs = 0
        self._total_processing_time = 0.0
        self._tables_generated = 0
        self._errors_expanded = 0

        self.buffer_manager.reset_statistics()
        self.pattern_detector.clear_patterns()
        self.aggregation_engine.reset_statistics()
        self.error_expansion_engine.reset_statistics()

        # Reset aggregator statistics (Stage 4.5)
        if hasattr(self, "operation_aggregator"):
            self.operation_aggregator.reset_stats()
        if hasattr(self, "value_aggregator"):
            self.value_aggregator.reset_stats()
