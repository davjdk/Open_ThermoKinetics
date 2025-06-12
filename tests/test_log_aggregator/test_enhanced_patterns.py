"""
Test module for enhanced pattern detection functionality (Stage 2).

Tests the new PatternGroup class and enhanced pattern detection methods
added in Stage 2 of the log aggregation system.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.pattern_detector import PATTERN_TYPES, PatternDetector, PatternGroup


class TestPatternGroup:
    """Test PatternGroup class functionality."""

    def test_pattern_group_creation(self):
        """Test basic PatternGroup creation."""
        # Create mock records
        records = [self._create_mock_record("Test message 1")]
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=1)
        metadata = {"test_key": "test_value"}

        pattern_group = PatternGroup(
            pattern_type="test_pattern", records=records, start_time=start_time, end_time=end_time, metadata=metadata
        )

        assert pattern_group.pattern_type == "test_pattern"
        assert pattern_group.records == records
        assert pattern_group.start_time == start_time
        assert pattern_group.end_time == end_time
        assert pattern_group.metadata == metadata

    def test_pattern_group_properties(self):
        """Test PatternGroup computed properties."""
        records = [self._create_mock_record("Message 1"), self._create_mock_record("Message 2")]
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)

        pattern_group = PatternGroup(
            pattern_type="test_pattern", records=records, start_time=start_time, end_time=end_time, metadata={}
        )

        assert pattern_group.count == 2
        assert pattern_group.duration == timedelta(seconds=5)

    def test_pattern_group_add_record(self):
        """Test adding records to PatternGroup."""
        start_time = datetime.now()
        pattern_group = PatternGroup(
            pattern_type="test_pattern", records=[], start_time=start_time, end_time=start_time, metadata={}
        )

        # Add a record
        new_record = self._create_mock_record("New message")
        pattern_group.add_record(new_record)

        assert pattern_group.count == 1
        assert new_record in pattern_group.records
        assert pattern_group.end_time == new_record.timestamp

    def test_get_table_suitable_flag(self):
        """Test table suitable flag retrieval."""
        # Test with table_suitable = True
        metadata = {"table_suitable": True}
        pattern_group = PatternGroup(
            pattern_type="test_pattern",
            records=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            metadata=metadata,
        )
        assert pattern_group.get_table_suitable_flag() is True

        # Test with table_suitable = False
        metadata = {"table_suitable": False}
        pattern_group.metadata = metadata
        assert pattern_group.get_table_suitable_flag() is False

        # Test without table_suitable key
        pattern_group.metadata = {}
        assert pattern_group.get_table_suitable_flag() is False

    def _create_mock_record(self, message: str) -> BufferedLogRecord:
        """Create a mock BufferedLogRecord for testing."""
        mock_log_record = MagicMock(spec=logging.LogRecord)
        mock_log_record.getMessage.return_value = message
        mock_log_record.levelname = "INFO"
        mock_log_record.name = "test_logger"

        return BufferedLogRecord(record=mock_log_record, timestamp=datetime.now())


class TestEnhancedPatternDetection:
    """Test enhanced pattern detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PatternDetector(similarity_threshold=0.8)

    def test_detect_pattern_groups_basic(self):
        """Test basic pattern group detection."""
        records = [
            self._create_mock_record("Adding a new line 'F1/3' to the plot."),
            self._create_mock_record("Adding a new line 'F3/4' to the plot."),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        assert pattern_groups[0].pattern_type == "plot_lines_addition"
        assert pattern_groups[0].count == 2

    def test_detect_plot_lines_pattern(self):
        """Test detection of plot lines addition pattern."""
        records = [
            self._create_mock_record("Adding a new line 'F1/3' to the plot."),
            self._create_mock_record("Adding a new line 'F3/4' to the plot."),
            self._create_mock_record("Adding a new line 'F2' to the plot."),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        group = pattern_groups[0]
        assert group.pattern_type == "plot_lines_addition"
        assert group.count == 3
        assert group.metadata["line_names"] == ["F1/3", "F3/4", "F2"]
        assert group.metadata["unique_lines"] == 3
        assert group.metadata["table_suitable"] is True

    def test_detect_cascade_initialization_pattern(self):
        """Test detection of cascade initialization pattern."""
        records = [
            self._create_mock_record_with_module("Initializing UserGuideTab"),
            self._create_mock_record_with_module("Initializing GuideFramework"),
            self._create_mock_record_with_module("Initializing ContentManager"),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        group = pattern_groups[0]
        assert group.pattern_type == "cascade_component_initialization"
        assert group.count == 3
        assert group.metadata["components"] == ["UserGuideTab", "GuideFramework", "ContentManager"]
        assert group.metadata["cascade_depth"] == 3
        assert group.metadata["table_suitable"] is True

    def test_detect_request_response_pattern(self):
        """Test detection of request-response cycle pattern."""
        records = [
            self._create_mock_record("Processing request for data"),
            self._create_mock_record("Handling request cycle"),
            self._create_mock_record("Sending response back"),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        group = pattern_groups[0]
        assert group.pattern_type == "request_response_cycle"
        assert group.count == 3
        assert group.metadata["request_count"] == 2
        assert group.metadata["response_count"] == 1
        assert group.metadata["table_suitable"] is True

    def test_detect_file_operations_pattern(self):
        """Test detection of file operations pattern."""
        records = [
            self._create_mock_record("Loading file data.csv"),
            self._create_mock_record("Reading configuration.json"),
            self._create_mock_record("Saving results.txt"),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        group = pattern_groups[0]
        assert group.pattern_type == "file_operations"
        assert group.count == 3
        assert "read" in group.metadata["operation_types"]
        assert "write" in group.metadata["operation_types"]
        assert "csv" in group.metadata["file_extensions"]
        assert "json" in group.metadata["file_extensions"]
        assert "txt" in group.metadata["file_extensions"]

    def test_detect_gui_updates_pattern(self):
        """Test detection of GUI updates pattern."""
        records = [
            self._create_mock_record("Updating widget display"),
            self._create_mock_record("Refreshing table view"),
            self._create_mock_record("Redrawing plot canvas"),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 1
        group = pattern_groups[0]
        assert group.pattern_type == "gui_updates"
        assert group.count == 3
        assert "update" in group.metadata["update_types"]
        assert "refresh" in group.metadata["update_types"]
        assert "redraw" in group.metadata["update_types"]

    def test_multiple_pattern_types(self):
        """Test detection of multiple different pattern types."""
        records = [
            # Plot lines pattern
            self._create_mock_record("Adding a new line 'F1/3' to the plot."),
            self._create_mock_record("Adding a new line 'F2' to the plot."),
            # File operations pattern
            self._create_mock_record("Loading data.csv"),
            self._create_mock_record("Saving results.json"),
            # Single record (should not create pattern)
            self._create_mock_record("Random single message"),
        ]

        pattern_groups = self.detector.detect_pattern_groups(records)

        assert len(pattern_groups) == 2

        # Check pattern types
        pattern_types = [group.pattern_type for group in pattern_groups]
        assert "plot_lines_addition" in pattern_types
        assert "file_operations" in pattern_types

    def test_empty_records(self):
        """Test handling of empty records list."""
        pattern_groups = self.detector.detect_pattern_groups([])
        assert pattern_groups == []

    def test_single_record_no_pattern(self):
        """Test that single records don't create patterns."""
        records = [self._create_mock_record("Single message")]
        pattern_groups = self.detector.detect_pattern_groups(records)
        assert len(pattern_groups) == 0

    def test_pattern_type_constants(self):
        """Test that pattern type constants are defined."""
        expected_types = [
            "plot_lines_addition",
            "cascade_component_initialization",
            "request_response_cycle",
            "file_operations",
            "gui_updates",
            "basic_similarity",
        ]

        for pattern_type in expected_types:
            assert pattern_type in PATTERN_TYPES

    def _create_mock_record(self, message: str) -> BufferedLogRecord:
        """Create a mock BufferedLogRecord for testing."""
        mock_log_record = MagicMock(spec=logging.LogRecord)
        mock_log_record.getMessage.return_value = message
        mock_log_record.levelname = "INFO"
        mock_log_record.name = "test_logger"

        return BufferedLogRecord(record=mock_log_record, timestamp=datetime.now())

    def _create_mock_record_with_module(self, message: str) -> BufferedLogRecord:
        """Create a mock BufferedLogRecord with module attribute for testing."""
        mock_log_record = MagicMock(spec=logging.LogRecord)
        mock_log_record.getMessage.return_value = message
        mock_log_record.levelname = "INFO"
        mock_log_record.name = "test_logger"
        mock_log_record.module = "test_module"

        return BufferedLogRecord(record=mock_log_record, timestamp=datetime.now())
