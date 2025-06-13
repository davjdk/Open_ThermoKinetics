"""
Unit tests for OperationTableBuilder - Stage 4 implementation.

This module tests the tabular representation functionality for operation metrics,
including various table types and formatting options.
"""

import unittest
from datetime import datetime

from src.log_aggregator.operation_monitor import OperationMetrics, OperationStatus
from src.log_aggregator.operation_table_builder import OperationTableBuilder, OperationTableData


class TestOperationTableBuilder(unittest.TestCase):
    """Test cases for OperationTableBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder = OperationTableBuilder()

        # Create sample operation metrics
        self.sample_operations = [
            OperationMetrics(
                operation_id="op_001",
                operation_type="DECONVOLUTION",
                module="CalculationEngine",
                start_time=datetime(2025, 6, 14, 10, 0, 0),
                end_time=datetime(2025, 6, 14, 10, 0, 5),
                status=OperationStatus.COMPLETED,
                duration_ms=5000.0,
                request_count=3,
                response_count=3,
                warning_count=1,
                error_count=0,
                memory_usage_mb=256.5,
                components_involved={"CalculationEngine", "GUI"},
                custom_metrics={
                    "file_count": 2,
                    "reaction_count": 4,
                    "mse_value": 0.00123,
                    "r_squared": 0.9876,
                    "method": "gauss",
                },
            ),
            OperationMetrics(
                operation_id="op_002",
                operation_type="MODEL_FIT_CALCULATION",
                module="Calculator",
                start_time=datetime(2025, 6, 14, 10, 1, 0),
                end_time=datetime(2025, 6, 14, 10, 1, 2),
                status=OperationStatus.COMPLETED,
                duration_ms=2500.0,
                request_count=1,
                response_count=1,
                warning_count=0,
                error_count=0,
                memory_usage_mb=128.0,
                components_involved={"Calculator"},
                custom_metrics={"reaction_count": 3, "r_squared": 0.9654, "method": "Coats-Redfern"},
            ),
            OperationMetrics(
                operation_id="op_003",
                operation_type="LOAD_FILE",
                module="FileManager",
                start_time=datetime(2025, 6, 14, 10, 2, 0),
                status=OperationStatus.FAILED,
                duration_ms=100.0,
                request_count=1,
                response_count=0,
                warning_count=0,
                error_count=1,
                error_message="File not found",
                components_involved={"FileManager"},
                custom_metrics={},
            ),
        ]

    def test_build_operation_summary_table(self):
        """Test building operation summary table."""
        table = self.builder.build_operation_summary_table(self.sample_operations)

        # Check basic structure
        self.assertIsInstance(table, OperationTableData)
        self.assertEqual(table.title, "Operation Summary")
        self.assertEqual(table.table_type, "operation_summary")

        # Check headers include base columns
        for base_col in self.builder.BASE_COLUMNS:
            self.assertIn(base_col, table.headers)

        # Check that optional columns are included when metrics are available
        self.assertIn("Requests", table.headers)  # request_count available
        self.assertIn("MSE", table.headers)  # mse_value available
        self.assertIn("R²", table.headers)  # r_squared available

        # Check number of rows
        self.assertEqual(len(table.rows), 3)

        # Check summary is generated
        self.assertIsNotNone(table.summary)
        self.assertIn("Total: 3 operations", table.summary)
        self.assertIn("Completed: 2", table.summary)
        self.assertIn("Failed: 1", table.summary)

        # Check metadata
        self.assertEqual(table.metadata["total_operations"], 3)
        self.assertIn("available_metrics", table.metadata)

    def test_build_operation_summary_table_empty(self):
        """Test building table with empty operations list."""
        table = self.builder.build_operation_summary_table([])

        self.assertEqual(table.title, "Operation Summary")
        self.assertEqual(len(table.rows), 1)
        self.assertEqual(table.rows[0][0], "No operations found")
        self.assertEqual(table.summary, "0 operations total")

    def test_build_metrics_detail_table(self):
        """Test building detailed metrics table for single operation."""
        operation = self.sample_operations[0]
        table = self.builder.build_metrics_detail_table(operation)

        # Check basic structure
        self.assertIsInstance(table, OperationTableData)
        self.assertEqual(table.table_type, "metrics_detail")
        self.assertIn("DECONVOLUTION", table.title)

        # Check headers
        self.assertEqual(table.headers, ["Metric", "Value"])

        # Check that basic metrics are included
        metric_names = [row[0] for row in table.rows]
        self.assertIn("Operation ID", metric_names)
        self.assertIn("Operation Type", metric_names)
        self.assertIn("Status", metric_names)
        self.assertIn("Duration", metric_names)
        self.assertIn("Requests", metric_names)
        self.assertIn("Responses", metric_names)
        self.assertIn("Warnings", metric_names)
        self.assertIn("Errors", metric_names)

        # Check custom metrics are included
        custom_metric_names = [row[0] for row in table.rows if row[0].startswith("Custom:")]
        self.assertTrue(len(custom_metric_names) > 0)
        self.assertIn("Custom: file_count", metric_names)
        self.assertIn("Custom: reaction_count", metric_names)

        # Check metadata
        self.assertEqual(table.metadata["operation_id"], "op_001")
        self.assertEqual(table.metadata["operation_type"], "DECONVOLUTION")

    def test_build_performance_metrics_table(self):
        """Test building performance metrics table."""
        table = self.builder.build_performance_metrics_table(self.sample_operations)

        # Check basic structure
        self.assertEqual(table.title, "Performance Metrics")
        self.assertEqual(table.table_type, "performance_metrics")

        # Check headers
        expected_headers = ["Operation", "Duration (ms)", "Memory (MB)", "CPU %", "Status", "Efficiency"]
        self.assertEqual(table.headers, expected_headers)

        # Check number of rows
        self.assertEqual(len(table.rows), 3)

        # Check that efficiency ratings are calculated
        for row in table.rows:
            efficiency = row[5]  # Efficiency column
            self.assertTrue(
                "Excellent" in efficiency
                or "Good" in efficiency
                or "Fair" in efficiency
                or "Poor" in efficiency
                or "N/A" in efficiency
            )

        # Check summary
        self.assertIsNotNone(table.summary)
        self.assertIn("Completed: 2/3", table.summary)

    def test_build_domain_specific_table_kinetics(self):
        """Test building domain-specific table for solid-state kinetics."""
        table = self.builder.build_domain_specific_table(self.sample_operations, domain="solid_state_kinetics")

        # Check basic structure
        self.assertEqual(table.title, "Solid-State Kinetics Analysis")
        self.assertEqual(table.table_type, "domain_specific")

        # Check kinetics-specific headers
        expected_headers = ["Analysis Step", "Duration (s)", "Files/Reactions", "Quality Metrics", "Status"]
        self.assertEqual(table.headers, expected_headers)

        # Check Files/Reactions column format
        for row in table.rows:
            files_reactions = row[2]
            if "F/" in files_reactions and "R" in files_reactions:
                # Check format: "XF/YR"
                parts = files_reactions.split("F/")
                self.assertEqual(len(parts), 2)
                self.assertTrue(parts[1].endswith("R"))

        # Check Quality Metrics column format
        quality_row = table.rows[0][3]  # First operation with quality metrics
        self.assertIn("MSE:", quality_row)
        self.assertIn("R²:", quality_row)

        # Check metadata
        self.assertEqual(table.metadata["domain"], "solid_state_kinetics")

    def test_build_domain_specific_table_fallback(self):
        """Test domain-specific table fallback to general summary."""
        table = self.builder.build_domain_specific_table(self.sample_operations, domain="unknown_domain")

        # Should fallback to operation summary
        self.assertEqual(table.table_type, "operation_summary")

    def test_format_status(self):
        """Test status formatting with icons."""
        # Test all status types
        completed_status = self.builder._format_status(OperationStatus.COMPLETED)
        self.assertIn("✅", completed_status)
        self.assertIn("COMPLETED", completed_status)

        failed_status = self.builder._format_status(OperationStatus.FAILED)
        self.assertIn("❌", failed_status)
        self.assertIn("FAILED", failed_status)

        timeout_status = self.builder._format_status(OperationStatus.TIMEOUT)
        self.assertIn("⏰", timeout_status)
        self.assertIn("TIMEOUT", timeout_status)

        running_status = self.builder._format_status(OperationStatus.RUNNING)
        self.assertIn("🔄", running_status)
        self.assertIn("RUNNING", running_status)

        pending_status = self.builder._format_status(OperationStatus.PENDING)
        self.assertIn("⏳", pending_status)
        self.assertIn("PENDING", pending_status)

    def test_format_metric_value(self):
        """Test metric value formatting."""
        # Test different value types
        self.assertEqual(self.builder._format_metric_value(None), "N/A")
        self.assertEqual(self.builder._format_metric_value(123.456789), "123.457")
        self.assertEqual(self.builder._format_metric_value([1, 2, 3]), "1, 2, 3")
        self.assertEqual(self.builder._format_metric_value("string_value"), "string_value")
        self.assertEqual(self.builder._format_metric_value(42), "42")

    def test_calculate_efficiency_rating(self):
        """Test efficiency rating calculation."""
        # Test completed operation
        completed_op = self.sample_operations[0]
        rating = self.builder._calculate_efficiency_rating(completed_op)
        self.assertNotEqual(rating, "N/A")
        self.assertTrue("Excellent" in rating or "Good" in rating or "Fair" in rating or "Poor" in rating)

        # Test failed operation
        failed_op = self.sample_operations[2]
        rating = self.builder._calculate_efficiency_rating(failed_op)
        self.assertEqual(rating, "N/A")

    def test_get_available_metrics(self):
        """Test detection of available metrics."""
        available = self.builder._get_available_metrics(self.sample_operations)

        # Should detect standard metrics
        self.assertIn("request_count", available)
        self.assertIn("memory_usage_mb", available)

        # Should detect custom metrics that are in OPTIONAL_COLUMNS
        self.assertIn("mse_value", available)
        self.assertIn("r_squared", available)
        self.assertIn("reaction_count", available)
        self.assertIn("method", available)

    def test_build_operation_row(self):
        """Test building individual operation row."""
        operation = self.sample_operations[0]
        headers = ["Sub-Operation", "Start Time", "Duration (s)", "Status", "MSE"]

        row = self.builder._build_operation_row(operation, headers)

        self.assertEqual(len(row), len(headers))
        self.assertEqual(row[0], "DECONVOLUTION")  # Sub-Operation
        self.assertEqual(row[1], "10:00:00")  # Start Time
        self.assertEqual(row[2], "5.000")  # Duration (s)
        self.assertIn("COMPLETED", row[3])  # Status
        self.assertEqual(row[4], "0.001")  # MSE

    def test_summary_generation(self):
        """Test summary string generation."""
        summary = self.builder._build_summary(self.sample_operations)

        # Check all expected components
        self.assertIn("Total: 3 operations", summary)
        self.assertIn("Completed: 2", summary)
        self.assertIn("Failed: 1", summary)
        self.assertIn("Timeout: 0", summary)
        self.assertIn("Total time:", summary)
        self.assertIn("Average:", summary)

    def test_performance_summary_generation(self):
        """Test performance summary generation."""
        summary = self.builder._build_performance_summary(self.sample_operations)

        self.assertIn("Completed: 2/3", summary)
        self.assertIn("Avg Duration:", summary)
        self.assertIn("Avg Memory:", summary)

    def test_kinetics_summary_generation(self):
        """Test kinetics-specific summary generation."""
        summary = self.builder._build_kinetics_summary(self.sample_operations)

        self.assertIn("Files processed:", summary)
        self.assertIn("Reactions analyzed:", summary)
        self.assertIn("Analysis steps:", summary)

        # Should include operation type counts
        self.assertIn("DECONVOLUTION(1)", summary)
        self.assertIn("MODEL_FIT_CALCULATION(1)", summary)
        self.assertIn("LOAD_FILE(1)", summary)

    def test_custom_title_and_settings(self):
        """Test custom title and builder settings."""
        # Test custom title
        custom_title = "My Custom Analysis"
        table = self.builder.build_operation_summary_table(self.sample_operations, title=custom_title)
        self.assertEqual(table.title, custom_title)

        # Test builder settings
        self.builder.float_precision = 2
        self.builder.date_format = "%H:%M"

        table = self.builder.build_operation_summary_table(self.sample_operations)

        # Check precision in duration column
        for row in table.rows:
            duration_idx = table.headers.index("Duration (s)")
            if row[duration_idx] != "N/A":
                # Should have 2 decimal places
                self.assertEqual(len(row[duration_idx].split(".")[1]), 2)

        # Check time format
        for row in table.rows:
            time_idx = table.headers.index("Start Time")
            if row[time_idx] != "N/A":
                # Should be HH:MM format
                self.assertEqual(len(row[time_idx]), 5)
                self.assertIn(":", row[time_idx])

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test with operation having no metrics
        minimal_op = OperationMetrics(
            operation_id="minimal",
            operation_type="MINIMAL_TEST",
            module="TestModule",
            start_time=datetime(2025, 6, 14, 12, 0, 0),
            status=OperationStatus.PENDING,
        )

        table = self.builder.build_metrics_detail_table(minimal_op)
        self.assertIsInstance(table, OperationTableData)

        # Test with None values
        table = self.builder.build_operation_summary_table([minimal_op])
        self.assertEqual(len(table.rows), 1)

        # Test empty custom metrics
        self.assertEqual(len(minimal_op.custom_metrics), 0)
        detail_table = self.builder.build_metrics_detail_table(minimal_op)
        # Should still have basic metrics
        self.assertTrue(len(detail_table.rows) > 5)


if __name__ == "__main__":
    unittest.main()
