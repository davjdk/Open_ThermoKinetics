"""
Tests for error expansion engine.

This module contains comprehensive tests for the ErrorExpansionEngine
including error classification, context analysis, and suggestion generation.
"""

import logging
from datetime import datetime, timedelta

import pytest

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.error_expansion import ErrorContext, ErrorExpansionConfig, ErrorExpansionEngine


class TestErrorExpansionEngine:
    """Test cases for ErrorExpansionEngine functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.config = ErrorExpansionConfig(
            enabled=True, context_lines=3, trace_depth=5, error_threshold_level="WARNING"
        )
        self.engine = ErrorExpansionEngine(self.config)

    def create_mock_record(
        self, level: int, message: str, filename: str = "test.py", lineno: int = 42, time_offset: float = 0
    ) -> BufferedLogRecord:
        """Create a mock log record for testing."""
        log_record = logging.LogRecord(
            name="test_logger",
            level=level,
            pathname=f"/path/to/{filename}",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None,
        )
        log_record.filename = filename
        timestamp = datetime.now() - timedelta(seconds=time_offset)
        return BufferedLogRecord(record=log_record, timestamp=timestamp)

    def test_error_classification_file_not_found(self):
        """Test classification of file not found errors."""
        message = "File not found: data.csv cannot be opened"
        keywords = self.engine._extract_keywords(message)
        classification = self.engine._classify_error(message, keywords)

        assert classification == "file_not_found"

    def test_error_classification_memory_error(self):
        """Test classification of memory errors."""
        message = "Memory allocation failed during matrix calculation"
        keywords = self.engine._extract_keywords(message)
        classification = self.engine._classify_error(message, keywords)

        assert classification == "memory_error"

    def test_error_classification_gui_error(self):
        """Test classification of GUI errors."""
        message = "Widget display error in main_window"
        keywords = self.engine._extract_keywords(message)
        classification = self.engine._classify_error(message, keywords)

        assert classification == "gui_error"

    def test_error_classification_calculation_error(self):
        """Test classification of calculation errors."""
        message = "Division by zero in deconvolution calculation"
        keywords = self.engine._extract_keywords(message)
        classification = self.engine._classify_error(message, keywords)

        assert classification == "calculation_error"

    def test_error_classification_operation_error(self):
        """Test classification of operation errors."""
        message = "Unknown operation OperationType.INVALID_OP"
        keywords = self.engine._extract_keywords(message)
        classification = self.engine._classify_error(message, keywords)

        assert classification == "operation_error"

    def test_keyword_extraction(self):
        """Test extraction of keywords from error messages."""
        message = "Error in file_data.py: OperationType.LOAD_FILE failed for data.csv"
        keywords = self.engine._extract_keywords(message)

        expected_keywords = ["file_data.py", "OperationType.LOAD_FILE", "data.csv"]
        for keyword in expected_keywords:
            assert keyword in keywords

    def test_is_error_record_warning(self):
        """Test identification of WARNING level records as errors."""
        record = self.create_mock_record(logging.WARNING, "Warning message")
        assert self.engine.is_error_record(record) is True

    def test_is_error_record_error(self):
        """Test identification of ERROR level records as errors."""
        record = self.create_mock_record(logging.ERROR, "Error message")
        assert self.engine.is_error_record(record) is True

    def test_is_error_record_info(self):
        """Test that INFO level records are not identified as errors."""
        record = self.create_mock_record(logging.INFO, "Info message")
        assert self.engine.is_error_record(record) is False

    def test_is_error_record_disabled(self):
        """Test that disabled engine doesn't identify any errors."""
        self.config.enabled = False
        engine = ErrorExpansionEngine(self.config)

        record = self.create_mock_record(logging.ERROR, "Error message")
        assert engine.is_error_record(record) is False

    def test_find_preceding_context(self):
        """Test finding preceding context records."""
        now = datetime.now()
        error_record = self.create_mock_record(logging.ERROR, "Error occurred")
        error_record.timestamp = now

        # Create context records
        context_records = []
        for i in range(5):
            record = self.create_mock_record(logging.INFO, f"Context message {i}")
            record.timestamp = now - timedelta(seconds=i + 1)
            context_records.append(record)

        preceding = self.engine._find_preceding_context(error_record, context_records)

        # Should return most recent records within time window
        assert len(preceding) <= self.config.context_lines
        for record in preceding:
            assert record.timestamp < error_record.timestamp

    def test_find_related_operations(self):
        """Test finding related operation records."""
        error_record = self.create_mock_record(logging.ERROR, "Error in file_data.py")

        # Create related and unrelated records
        context_records = [
            self.create_mock_record(logging.INFO, "Processing file_data.py"),
            self.create_mock_record(logging.INFO, "Loading data.csv"),
            self.create_mock_record(logging.INFO, "Unrelated message"),
            self.create_mock_record(logging.INFO, "Another file_data operation"),
        ]

        related = self.engine._find_related_operations(error_record, context_records)

        # Should find records with common keywords
        assert len(related) > 0
        # Records with file_data.py should be prioritized
        assert any("file_data.py" in record.record.getMessage() for record in related)

    def test_generate_suggestions_file_error(self):
        """Test suggestion generation for file errors."""
        error_record = self.create_mock_record(logging.ERROR, "File not found: data.csv")
        suggestions = self.engine._generate_suggestions("file_not_found", ["data.csv"], error_record)

        assert len(suggestions) > 0
        assert any("file" in suggestion.lower() for suggestion in suggestions)
        assert any("path" in suggestion.lower() for suggestion in suggestions)

    def test_generate_suggestions_with_location(self):
        """Test that suggestions include file location information."""
        error_record = self.create_mock_record(logging.ERROR, "Error occurred", "data_loader.py", 123)
        suggestions = self.engine._generate_suggestions("file_not_found", [], error_record)

        # Should include location-specific suggestion

        location_suggestion = next((s for s in suggestions if "data_loader.py:123" in s), None)
        assert location_suggestion is not None

    def test_expand_error_full_workflow(self):
        """Test complete error expansion workflow."""
        # Create error record
        error_record = self.create_mock_record(logging.ERROR, "File not found: data.csv")

        # Create context records with earlier timestamps
        context_records = [
            self.create_mock_record(logging.INFO, "Loading file data.csv", time_offset=5),
            self.create_mock_record(logging.INFO, "Initializing file loader", time_offset=8),
            self.create_mock_record(logging.DEBUG, "Setting up data processing", time_offset=9),
        ]

        # Expand error
        expanded_record = self.engine.expand_error(error_record, context_records)

        # Verify expansion
        assert expanded_record is not None
        assert hasattr(expanded_record.record, "error_expansion")
        assert expanded_record.record.error_expansion is True
        assert hasattr(expanded_record.record, "error_classification")

        # Check that expanded message contains context information
        expanded_message = expanded_record.record.getMessage()
        assert "DETAILED ERROR ANALYSIS" in expanded_message
        assert "PRECEDING CONTEXT" in expanded_message
        assert "SUGGESTED ACTIONS" in expanded_message

    def test_statistics_tracking(self):
        """Test that statistics are properly tracked."""
        initial_stats = self.engine.get_statistics()

        # Expand an error
        error_record = self.create_mock_record(logging.ERROR, "Test error")
        context_records = []
        self.engine.expand_error(error_record, context_records)

        # Check updated statistics
        final_stats = self.engine.get_statistics()
        assert final_stats["errors_analyzed"] == initial_stats["errors_analyzed"] + 1
        assert final_stats["contexts_generated"] == initial_stats["contexts_generated"] + 1

    def test_statistics_reset(self):
        """Test statistics reset functionality."""
        # Generate some statistics
        error_record = self.create_mock_record(logging.ERROR, "Test error")
        self.engine.expand_error(error_record, [])

        # Reset and verify
        self.engine.reset_statistics()
        stats = self.engine.get_statistics()

        for value in stats.values():
            assert value == 0

    def test_error_context_dataclass(self):
        """Test ErrorContext dataclass functionality."""
        error_record = self.create_mock_record(logging.ERROR, "Test error")

        context = ErrorContext(
            error_record=error_record, error_classification="test_error", suggested_actions=["Action 1", "Action 2"]
        )

        assert context.error_record == error_record
        assert context.error_classification == "test_error"
        assert len(context.suggested_actions) == 2
        assert context.preceding_records == []  # Default empty list

    def test_error_threshold_levels(self):
        """Test different error threshold levels."""
        # Test WARNING threshold
        config_warning = ErrorExpansionConfig(error_threshold_level="WARNING")
        engine_warning = ErrorExpansionEngine(config_warning)

        assert engine_warning.is_error_record(self.create_mock_record(logging.WARNING, "Warning")) is True
        assert engine_warning.is_error_record(self.create_mock_record(logging.INFO, "Info")) is False

        # Test ERROR threshold
        config_error = ErrorExpansionConfig(error_threshold_level="ERROR")
        engine_error = ErrorExpansionEngine(config_error)

        assert engine_error.is_error_record(self.create_mock_record(logging.WARNING, "Warning")) is False
        assert engine_error.is_error_record(self.create_mock_record(logging.ERROR, "Error")) is True

    def test_context_time_window(self):
        """Test context time window functionality."""
        now = datetime.now()
        error_record = self.create_mock_record(logging.ERROR, "Error")
        error_record.timestamp = now

        # Create records outside time window
        old_record = self.create_mock_record(logging.INFO, "Old message")
        old_record.timestamp = now - timedelta(seconds=20)  # Outside default 10s window

        # Create record within time window
        recent_record = self.create_mock_record(logging.INFO, "Recent message")
        recent_record.timestamp = now - timedelta(seconds=5)  # Within window

        context_records = [old_record, recent_record]
        preceding = self.engine._find_preceding_context(error_record, context_records)

        # Should only include recent record
        assert len(preceding) == 1
        assert preceding[0] == recent_record


class TestErrorExpansionConfig:
    """Test cases for ErrorExpansionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ErrorExpansionConfig()

        assert config.enabled is True
        assert config.context_lines == 5
        assert config.trace_depth == 10
        assert config.immediate_expansion is True
        assert config.error_threshold_level == "WARNING"
        assert config.context_time_window == 10.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ErrorExpansionConfig(enabled=False, context_lines=3, trace_depth=7, error_threshold_level="ERROR")

        assert config.enabled is False
        assert config.context_lines == 3
        assert config.trace_depth == 7
        assert config.error_threshold_level == "ERROR"


@pytest.fixture
def sample_error_record():
    """Fixture providing a sample error record for tests."""
    log_record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="/path/to/test.py",
        lineno=42,
        msg="Sample error message",
        args=(),
        exc_info=None,
    )
    log_record.filename = "test.py"
    return BufferedLogRecord(record=log_record, timestamp=datetime.now())


@pytest.fixture
def sample_context_records():
    """Fixture providing sample context records for tests."""
    records = []
    base_time = datetime.now()

    for i in range(5):
        log_record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=f"/path/to/context_{i}.py",
            lineno=10 + i,
            msg=f"Context message {i}",
            args=(),
            exc_info=None,
        )
        log_record.filename = f"context_{i}.py"
        buffered_record = BufferedLogRecord(record=log_record, timestamp=base_time - timedelta(seconds=i + 1))
        records.append(buffered_record)

    return records
