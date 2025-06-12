"""
Test module for enhanced aggregation engine functionality (Stage 2).

Tests the enhanced AggregationEngine methods that work with PatternGroup
objects and provide enhanced metadata and statistics.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.log_aggregator.aggregation_engine import AggregationEngine
from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.pattern_detector import PatternGroup


class TestEnhancedAggregationEngine:
    """Test enhanced aggregation engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AggregationEngine(min_pattern_entries=2)

    def test_aggregate_pattern_groups_basic(self):
        """Test basic pattern group aggregation."""
        # Create test pattern group
        records = [
            self._create_mock_record("Adding a new line 'F1/3' to the plot."),
            self._create_mock_record("Adding a new line 'F2' to the plot."),
        ]

        pattern_group = PatternGroup(
            pattern_type="plot_lines_addition",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=1),
            metadata={"line_names": ["F1/3", "F2"], "table_suitable": True, "unique_lines": 2},
        )

        aggregated_records = self.engine.aggregate_pattern_groups([pattern_group])

        assert len(aggregated_records) == 1
        record = aggregated_records[0]
        assert record.pattern_id == "plot_lines_addition_2"
        assert record.count == 2
        assert "F1/3" in record.template
        assert "F2" in record.template

    def test_create_enhanced_template_plot_lines(self):
        """Test enhanced template creation for plot lines pattern."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="plot_lines_addition",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"line_names": ["F1/3", "F2", "F3"]},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "Adding plot lines: F1/3, F2, F3" == template

    def test_create_enhanced_template_cascade(self):
        """Test enhanced template creation for cascade initialization pattern."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="cascade_component_initialization",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"components": ["ComponentA", "ComponentB", "ComponentC"]},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "Cascade initialization: ComponentA → ComponentB → ComponentC" == template

    def test_create_enhanced_template_request_response(self):
        """Test enhanced template creation for request-response pattern."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="request_response_cycle",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"request_count": 5, "response_count": 3},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "Request-response cycle: 5 requests, 3 responses" == template

    def test_create_enhanced_template_file_operations(self):
        """Test enhanced template creation for file operations pattern."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="file_operations",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"operation_types": ["read", "write"], "file_extensions": ["csv", "json"]},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "File operations: read, write on csv, json files" == template

    def test_create_enhanced_template_gui_updates(self):
        """Test enhanced template creation for GUI updates pattern."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="gui_updates",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"update_types": ["refresh", "redraw"]},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "GUI updates: refresh, redraw" == template

    def test_create_enhanced_template_long_lists(self):
        """Test enhanced template creation with long lists (truncation)."""
        records = [self._create_mock_record("Test message")]
        pattern_group = PatternGroup(
            pattern_type="plot_lines_addition",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={"line_names": ["F1", "F2", "F3", "F4", "F5"]},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "Adding plot lines: F1, F2, F3..." == template

    def test_create_enhanced_template_unknown_pattern(self):
        """Test enhanced template creation for unknown pattern type."""
        records = [self._create_mock_record("Test original message")]
        pattern_group = PatternGroup(
            pattern_type="unknown_pattern",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={},
        )

        template = self.engine._create_enhanced_template(pattern_group)
        assert "Test original message" == template

    def test_get_pattern_type_statistics(self):
        """Test pattern type statistics generation."""
        # Create multiple pattern groups of different types
        pattern_groups = [
            PatternGroup(
                pattern_type="plot_lines_addition",
                records=[self._create_mock_record("msg1"), self._create_mock_record("msg2")],
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(milliseconds=100),
                metadata={"table_suitable": True},
            ),
            PatternGroup(
                pattern_type="plot_lines_addition",
                records=[self._create_mock_record("msg3")],
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(milliseconds=50),
                metadata={"table_suitable": True},
            ),
            PatternGroup(
                pattern_type="file_operations",
                records=[self._create_mock_record("msg4"), self._create_mock_record("msg5")],
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(milliseconds=200),
                metadata={"table_suitable": False},
            ),
        ]

        stats = self.engine.get_pattern_type_statistics(pattern_groups)

        # Check plot_lines_addition stats
        plot_stats = stats["plot_lines_addition"]
        assert plot_stats["count"] == 2
        assert plot_stats["total_records"] == 3
        assert plot_stats["table_suitable"] == 2
        assert plot_stats["avg_records_per_group"] == 1.5

        # Check file_operations stats
        file_stats = stats["file_operations"]
        assert file_stats["count"] == 1
        assert file_stats["total_records"] == 2
        assert file_stats["table_suitable"] == 0
        assert file_stats["avg_records_per_group"] == 2.0

    def test_process_enhanced_records(self):
        """Test the main enhanced processing method."""
        records = [
            self._create_mock_record("Adding a new line 'F1/3' to the plot."),
            self._create_mock_record("Adding a new line 'F2' to the plot."),
        ]

        pattern_groups = [
            PatternGroup(
                pattern_type="plot_lines_addition",
                records=records,
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(seconds=1),
                metadata={"line_names": ["F1/3", "F2"], "table_suitable": True},
            )
        ]

        aggregated_records = self.engine.process_enhanced_records(records, pattern_groups)

        assert len(aggregated_records) == 1
        assert aggregated_records[0].count == 2
        assert "F1/3" in aggregated_records[0].template

    def test_minimum_pattern_entries_filter(self):
        """Test that patterns below minimum entries are filtered out."""
        # Create pattern group with only 1 record (below minimum of 2)
        records = [self._create_mock_record("Single message")]
        pattern_group = PatternGroup(
            pattern_type="test_pattern",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={},
        )

        aggregated_records = self.engine.aggregate_pattern_groups([pattern_group])

        assert len(aggregated_records) == 0

    def test_empty_pattern_groups(self):
        """Test handling of empty pattern groups list."""
        aggregated_records = self.engine.aggregate_pattern_groups([])
        assert aggregated_records == []

    def test_statistics_update_with_pattern_groups(self):
        """Test that statistics are properly updated when processing pattern groups."""
        initial_stats = self.engine.get_statistics()

        records = [
            self._create_mock_record("Message 1"),
            self._create_mock_record("Message 2"),
        ]

        pattern_group = PatternGroup(
            pattern_type="test_pattern",
            records=records,
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata={},
        )

        self.engine.aggregate_pattern_groups([pattern_group])

        updated_stats = self.engine.get_statistics()

        assert updated_stats["total_patterns_processed"] == initial_stats["total_patterns_processed"] + 1
        assert updated_stats["total_records_aggregated"] == initial_stats["total_records_aggregated"] + 2
        assert updated_stats["total_aggregations_created"] == initial_stats["total_aggregations_created"] + 1

    def _create_mock_record(self, message: str) -> BufferedLogRecord:
        """Create a mock BufferedLogRecord for testing."""
        mock_log_record = MagicMock(spec=logging.LogRecord)
        mock_log_record.getMessage.return_value = message
        mock_log_record.levelname = "INFO"
        mock_log_record.name = "test_logger"

        return BufferedLogRecord(record=mock_log_record, timestamp=datetime.now())
