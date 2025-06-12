"""
Tests for TabularFormatter module.

This module contains comprehensive tests for the TabularFormatter class
that validates table creation and ASCII formatting functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

from src.log_aggregator.buffer_manager import BufferedLogRecord
from src.log_aggregator.pattern_detector import PatternGroup
from src.log_aggregator.tabular_formatter import TableData, TabularFormatter, TabularFormattingConfig


class TestTabularFormatter:
    """Test suite for TabularFormatter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TabularFormattingConfig(
            enabled=True, max_table_width=80, max_rows_per_table=5, ascii_tables=True, include_summaries=True
        )
        self.formatter = TabularFormatter(self.config)

    def test_formatter_initialization(self):
        """Test formatter initialization with custom config."""
        assert self.formatter.config.enabled is True
        assert self.formatter.config.max_table_width == 80
        assert self.formatter.config.max_rows_per_table == 5

    def test_format_patterns_as_tables_disabled(self):
        """Test that no tables are created when formatting is disabled."""
        self.config.enabled = False
        patterns = [self._create_mock_pattern()]

        result = self.formatter.format_patterns_as_tables(patterns)

        assert result == []

    def test_should_format_pattern_valid(self):
        """Test pattern should be formatted when conditions are met."""
        pattern = self._create_mock_pattern(pattern_type="plot_lines_addition", record_count=3, table_suitable=True)

        result = self.formatter._should_format_pattern(pattern)

        assert result is True

    def test_should_format_pattern_invalid_type(self):
        """Test pattern should not be formatted for unsupported types."""
        pattern = self._create_mock_pattern(pattern_type="unsupported_type", record_count=3, table_suitable=True)

        result = self.formatter._should_format_pattern(pattern)

        assert result is False

    def test_should_format_pattern_insufficient_records(self):
        """Test pattern should not be formatted with too few records."""
        pattern = self._create_mock_pattern(pattern_type="plot_lines_addition", record_count=1, table_suitable=True)

        result = self.formatter._should_format_pattern(pattern)

        assert result is False

    def test_create_plot_lines_table(self):
        """Test creation of plot lines addition table."""
        pattern = self._create_mock_pattern(pattern_type="plot_lines_addition", record_count=3)

        # Mock records with plot line messages
        records = [
            self._create_mock_record("Adding line F1/3 to plot", datetime.now()),
            self._create_mock_record("Adding line F3/4 to plot", datetime.now() + timedelta(milliseconds=50)),
            self._create_mock_record("Adding line F2 to plot", datetime.now() + timedelta(milliseconds=100)),
        ]
        pattern.records = records

        result = self.formatter._create_plot_lines_table(pattern)

        assert isinstance(result, TableData)
        assert result.title == "📊 Plot Lines Addition Summary"
        assert len(result.headers) == 5
        assert len(result.rows) == 3
        assert result.summary is not None

    def test_create_initialization_table(self):
        """Test creation of component initialization table."""
        pattern = self._create_mock_pattern(pattern_type="cascade_component_initialization", record_count=3)

        records = [
            self._create_mock_record("Initializing UserGuideTab", datetime.now()),
            self._create_mock_record("Creating GuideFramework", datetime.now() + timedelta(milliseconds=125)),
            self._create_mock_record("ContentManager initialized", datetime.now() + timedelta(milliseconds=250)),
        ]
        pattern.records = records

        result = self.formatter._create_initialization_table(pattern)

        assert isinstance(result, TableData)
        assert result.title == "🔧 Component Initialization Cascade"
        assert len(result.headers) == 5
        assert len(result.rows) == 3

    def test_create_request_response_table(self):
        """Test creation of request-response cycles table."""
        pattern = self._create_mock_pattern(pattern_type="request_response_cycle", record_count=4)

        records = [
            self._create_mock_record("UPDATE_VALUE request sent", datetime.now()),
            self._create_mock_record("UPDATE_VALUE response received", datetime.now() + timedelta(milliseconds=15)),
            self._create_mock_record("SET_VALUE request sent", datetime.now() + timedelta(milliseconds=30)),
            self._create_mock_record("SET_VALUE response received", datetime.now() + timedelta(milliseconds=40)),
        ]
        pattern.records = records

        result = self.formatter._create_request_response_table(pattern)

        assert isinstance(result, TableData)
        assert result.title == "🔄 Request-Response Cycles"
        assert len(result.headers) == 5
        assert len(result.rows) == 2  # 2 pairs

    def test_create_file_operations_table(self):
        """Test creation of file operations table."""
        pattern = self._create_mock_pattern(pattern_type="file_operations", record_count=3)

        records = [
            self._create_mock_record("Loading file NH4_rate_3.csv", datetime.now()),
            self._create_mock_record("Loading file NH4_rate_5.csv", datetime.now() + timedelta(seconds=14)),
            self._create_mock_record("Processing TO_A_T function", datetime.now() + timedelta(seconds=17)),
        ]
        pattern.records = records

        result = self.formatter._create_file_operations_table(pattern)

        assert isinstance(result, TableData)
        assert result.title == "📁 File Operations Summary"
        assert len(result.headers) == 5
        assert len(result.rows) == 3

    def test_create_gui_updates_table(self):
        """Test creation of GUI updates table."""
        pattern = self._create_mock_pattern(pattern_type="gui_updates", record_count=3)

        records = [
            self._create_mock_record("PlotCanvas adding line", datetime.now()),
            self._create_mock_record("SideBar set active item", datetime.now() + timedelta(milliseconds=45)),
            self._create_mock_record("CoefficientsView received update", datetime.now() + timedelta(milliseconds=103)),
        ]
        pattern.records = records

        result = self.formatter._create_gui_updates_table(pattern)

        assert isinstance(result, TableData)
        assert result.title == "🖥️ GUI Updates Batch"
        assert len(result.headers) == 5
        assert len(result.rows) == 3

    def test_format_ascii_table_basic(self):
        """Test basic ASCII table formatting."""
        table_data = TableData(
            title="Test Table",
            headers=["#", "Name", "Value"],
            rows=[["1", "First", "100"], ["2", "Second", "200"]],
            summary="Test summary",
            table_type="test",
        )

        result = self.formatter._format_ascii_table(table_data)

        assert "┌" in result
        assert "└" in result
        assert "│" in result
        assert "─" in result
        assert "Test Table" in result
        assert "Test summary" in result

    def test_format_ascii_table_empty_rows(self):
        """Test ASCII table formatting with empty rows."""
        table_data = TableData(title="Empty Table", headers=["#", "Name"], rows=[], table_type="test")

        result = self.formatter._format_ascii_table(table_data)

        assert "No data available" in result

    def test_calculate_column_widths(self):
        """Test column width calculation."""
        headers = ["#", "Name", "Value"]
        rows = [["1", "Short", "100"], ["2", "Very Long Name", "200"]]

        result = self.formatter._calculate_column_widths(headers, rows)

        assert result[0] == 1  # "#"
        assert result[1] == 14  # "Very Long Name"
        assert result[2] == 5  # "Value"    def test_adjust_column_widths(self):
        """Test column width adjustment for max table width."""
        col_widths = [10, 50, 30]  # Total 90
        headers = ["#", "Name", "Value"]
        rows = []

        # Set max width to 60, should proportionally reduce
        self.formatter.config.max_table_width = 60

        result = self.formatter._adjust_column_widths(col_widths, headers, rows)

        total_adjusted = sum(result)
        # Content area = max_width - (num_cols * 3) - 1 = 60 - 9 - 1 = 50
        max_content_width = 60 - len(col_widths) * 3 - 1
        assert total_adjusted <= max_content_width + 1  # Allow small rounding error

    def test_group_request_response_pairs(self):
        """Test grouping of request-response records."""
        records = [
            self._create_mock_record("UPDATE_VALUE request", datetime.now()),
            self._create_mock_record("UPDATE_VALUE response", datetime.now()),
            self._create_mock_record("SET_VALUE request", datetime.now()),
            # Missing response for last request
        ]

        result = self.formatter._group_request_response_pairs(records)

        assert len(result) == 2
        assert result[0][1] is not None  # First pair has response
        assert result[1][1] is None  # Second pair missing response

    def test_extract_line_name(self):
        """Test extraction of line names from messages."""
        test_cases = [
            ("Adding line 'F1/3' to plot", "F1/3"),
            ("plotting F3/4 model", "F3/4"),
            ("F2 kinetic model", "F2"),
            ("unknown message format", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_line_name(message)
            assert result == expected

    def test_extract_component_name(self):
        """Test extraction of component names from messages."""
        test_cases = [
            ("Initializing UserGuideTab", "UserGuideTab"),
            ("Creating GuideFramework", "GuideFramework"),
            ("ContentManager initialized", "ContentManager"),
            ("unknown message", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_component_name(message)
            assert result == expected

    def test_extract_operation_type(self):
        """Test extraction of operation types from messages."""
        test_cases = [
            ("Operation: UPDATE_VALUE", "UPDATE_VALUE"),
            ("SET_VALUE request sent", "SET_VALUE"),
            ("Request: GET_VALUE", "GET_VALUE"),
            ("unknown format", "UNKNOWN"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_operation_type(message)
            assert result == expected

    def test_extract_file_name(self):
        """Test extraction of file names from messages."""
        test_cases = [
            ("Loading file 'NH4_rate_3.csv'", "NH4_rate_3.csv"),
            ("loading data.txt", "data.txt"),
            ("Processing experiment.json", "experiment.json"),
            ("no file mentioned", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_file_name(message)
            assert result == expected

    def test_extract_file_operation(self):
        """Test extraction of file operation types."""
        test_cases = [
            ("Loading file data", "Load"),
            ("Save data to file", "Save"),
            ("Processing file content", "Process"),
            ("Export results", "Export"),
            ("Import configuration", "Import"),
            ("unknown operation", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_file_operation(message)
            assert result == expected

    def test_extract_gui_component(self):
        """Test extraction of GUI component names."""
        test_cases = [
            ("PlotCanvas updated", "PlotCanvas"),
            ("sidebar refresh", "SideBar"),
            ("MainWindow event", "MainWindow"),
            ("unknown component", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_gui_component(message)
            assert result == expected

    def test_extract_gui_update_type(self):
        """Test extraction of GUI update types."""
        test_cases = [
            ("add new element", "AddLine"),
            ("update existing", "Update"),
            ("set active item", "SetActive"),
            ("receive notification", "Received"),
            ("refresh display", "Refresh"),
            ("unknown action", "Unknown"),
        ]

        for message, expected in test_cases:
            result = self.formatter._extract_gui_update_type(message)
            assert result == expected

    def test_toggle_tabular_format(self):
        """Test toggling of tabular formatting."""
        assert self.formatter.config.enabled is True

        self.formatter.toggle_tabular_format(False)
        assert self.formatter.config.enabled is False

        self.formatter.toggle_tabular_format(True)
        assert self.formatter.config.enabled is True

    def test_create_table_record(self):
        """Test creation of table log record."""
        pattern = self._create_mock_pattern()
        formatted_table = "Test table content"

        result = self.formatter._create_table_record(formatted_table, pattern)

        assert isinstance(result, BufferedLogRecord)
        assert result.record.getMessage() == formatted_table
        assert result.record.name == "log_aggregator.tabular_formatter"

    def test_create_error_record(self):
        """Test creation of error log record."""
        error_message = "Test error message"

        result = self.formatter._create_error_record(error_message)

        assert isinstance(result, BufferedLogRecord)
        assert "[TABULAR_FORMAT_ERROR]" in result.record.getMessage()
        assert error_message in result.record.getMessage()

    def test_format_patterns_integration(self):
        """Test full integration of pattern formatting."""
        pattern = self._create_mock_pattern(pattern_type="plot_lines_addition", record_count=2, table_suitable=True)

        records = [
            self._create_mock_record("Adding F1/3 line", datetime.now()),
            self._create_mock_record("Adding F2 line", datetime.now() + timedelta(milliseconds=50)),
        ]
        pattern.records = records

        result = self.formatter.format_patterns_as_tables([pattern])

        assert len(result) == 1
        assert isinstance(result[0], BufferedLogRecord)
        assert "📊 Plot Lines Addition Summary" in result[0].record.getMessage()

    # Helper methods

    def _create_mock_pattern(self, pattern_type="plot_lines_addition", record_count=3, table_suitable=True):
        """Create a mock PatternGroup for testing."""
        pattern = Mock(spec=PatternGroup)
        pattern.pattern_type = pattern_type
        pattern.count = record_count
        pattern.records = [Mock() for _ in range(record_count)]
        pattern.start_time = datetime.now()
        pattern.end_time = datetime.now() + timedelta(milliseconds=100)
        pattern.get_table_suitable_flag.return_value = table_suitable
        return pattern

    def _create_mock_record(self, message, timestamp):
        """Create a mock BufferedLogRecord for testing."""
        # Create a mock LogRecord first
        log_record = Mock()
        log_record.getMessage.return_value = message
        log_record.name = "test.logger"
        log_record.levelno = 20

        # Create the BufferedLogRecord
        record = Mock(spec=BufferedLogRecord)
        record.record = log_record
        record.timestamp = timestamp
        return record


class TestTabularFormattingConfig:
    """Test suite for TabularFormattingConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TabularFormattingConfig()

        assert config.enabled is True
        assert config.max_table_width == 120
        assert config.max_rows_per_table == 20
        assert config.ascii_tables is True
        assert config.include_summaries is True
        assert len(config.auto_format_patterns) == 5

    def test_auto_format_patterns_initialization(self):
        """Test auto format patterns default initialization."""
        config = TabularFormattingConfig()

        expected_patterns = [
            "plot_lines_addition",
            "cascade_component_initialization",
            "request_response_cycle",
            "file_operations",
            "gui_updates",
        ]

        assert config.auto_format_patterns == expected_patterns

    def test_custom_config(self):
        """Test custom configuration values."""
        custom_patterns = ["custom_pattern1", "custom_pattern2"]

        config = TabularFormattingConfig(
            enabled=False, max_table_width=80, max_rows_per_table=10, auto_format_patterns=custom_patterns
        )

        assert config.enabled is False
        assert config.max_table_width == 80
        assert config.max_rows_per_table == 10
        assert config.auto_format_patterns == custom_patterns


class TestTableData:
    """Test suite for TableData dataclass."""

    def test_table_data_creation(self):
        """Test TableData creation with all fields."""
        table_data = TableData(
            title="Test Title",
            headers=["Col1", "Col2"],
            rows=[["val1", "val2"]],
            summary="Test summary",
            table_type="test_type",
        )

        assert table_data.title == "Test Title"
        assert table_data.headers == ["Col1", "Col2"]
        assert table_data.rows == [["val1", "val2"]]
        assert table_data.summary == "Test summary"
        assert table_data.table_type == "test_type"

    def test_table_data_defaults(self):
        """Test TableData with default values."""
        table_data = TableData(title="Test", headers=["Col1"], rows=[["val1"]])

        assert table_data.summary is None
        assert table_data.table_type == "generic"
