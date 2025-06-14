"""
Test script for Stage 6: Automatic Decorator Application

This script tests the automatic decorator application system to ensure
all OperationType operations are properly decorated.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.core.app_settings import OperationType
from src.core.logger_config import logger
from src.log_aggregator.automatic_decorator_application import (
    AutoDecorationConfig,
    AutomaticDecoratorApplicator,
    apply_automatic_decorators,
    get_decorated_method_info,
)


class TestStage6AutomaticDecoration(unittest.TestCase):
    """Test cases for Stage 6 automatic decorator application."""

    def setUp(self):
        """Set up test environment."""
        self.applicator = AutomaticDecoratorApplicator()

    def test_operation_method_mapping_coverage(self):
        """Test that all OperationType operations are mapped to methods."""
        mapping = self.applicator.operation_method_mapping

        # Check that we have mappings for major operation types
        expected_operations = [
            OperationType.ADD_REACTION,
            OperationType.REMOVE_REACTION,
            OperationType.DECONVOLUTION,
            OperationType.LOAD_FILE,
            OperationType.ADD_NEW_SERIES,
            OperationType.MODEL_FIT_CALCULATION,
            OperationType.MODEL_FREE_CALCULATION,
        ]

        for operation in expected_operations:
            self.assertIn(operation, mapping, f"Missing mapping for {operation}")
            self.assertIsInstance(mapping[operation], list)
            self.assertGreater(len(mapping[operation]), 0, f"Empty mapping for {operation}")

    def test_baseslots_subclass_detection(self):
        """Test detection of BaseSlots subclasses."""
        try:
            from src.core.base_signals import BaseSlots

            subclasses = self.applicator._get_all_baseslots_subclasses(BaseSlots)

            # Should find several subclasses
            self.assertGreater(len(subclasses), 0, "No BaseSlots subclasses found")

            # Check for known subclasses
            subclass_names = {cls.__name__ for cls in subclasses}
            expected_classes = ["CalculationsDataOperations", "FileData", "SeriesData", "CalculationsData"]

            for expected_class in expected_classes:
                self.assertIn(expected_class, subclass_names, f"Expected class {expected_class} not found")

        except ImportError:
            self.skipTest("BaseSlots not available for testing")

    def test_method_decoration_logic(self):
        """Test the method decoration logic."""

        # Create a mock class with methods
        class MockClass:
            def add_reaction(self):
                pass

            def remove_reaction(self):
                pass

            def _private_method(self):
                pass

            def process_request(self):
                pass

        # Mock the operation decorator
        with patch("src.log_aggregator.automatic_decorator_application.operation") as mock_operation:
            mock_decorator = MagicMock()
            mock_operation.return_value = mock_decorator
            mock_decorator.return_value = lambda x: x  # Return original method

            decorated_methods = self.applicator._decorate_class_methods(MockClass)

            # Should have decorated add_reaction and remove_reaction
            self.assertIn("add_reaction", decorated_methods)
            self.assertIn("remove_reaction", decorated_methods)
            self.assertIn("process_request", decorated_methods)

            # Should not decorate private methods
            self.assertNotIn("_private_method", decorated_methods)

            # Check that operation decorator was called
            self.assertTrue(mock_operation.called)

    def test_decoration_validation(self):
        """Test the decoration validation logic."""

        # Create a mock class with decorated and undecorated methods
        class MockClass:
            def decorated_method(self):
                pass

            def undecorated_method(self):
                pass

            def process_request(self):
                pass

        # Mark one method as decorated
        MockClass.decorated_method._is_operation_decorated = True
        MockClass.process_request._is_operation_decorated = True

        warnings = self.applicator._validate_class_decoration(MockClass)

        # Should not have warnings for properly decorated class
        self.assertEqual(len(warnings), 0, f"Unexpected warnings: {warnings}")

    def test_automatic_decorator_configuration(self):
        """Test the AutoDecorationConfig settings."""
        # Test that configuration exists and has expected settings
        self.assertTrue(hasattr(AutoDecorationConfig, "ENABLED"))
        self.assertTrue(hasattr(AutoDecorationConfig, "STRICT_MATCHING"))
        self.assertTrue(hasattr(AutoDecorationConfig, "PRESERVE_PYQT_METADATA"))
        self.assertTrue(hasattr(AutoDecorationConfig, "EXCLUSIONS"))

        # Test exclusions list
        exclusions = AutoDecorationConfig.EXCLUSIONS
        self.assertIn("__init__", exclusions)
        self.assertIn("connect_to_dispatcher", exclusions)

    def test_get_decorated_method_info(self):
        """Test getting information about decorated methods."""

        # Create a mock class with a method
        class MockClass:
            def test_method(self):
                pass

        # Test with non-existent method
        info = get_decorated_method_info(MockClass, "nonexistent")
        self.assertFalse(info["exists"])

        # Test with existing method
        info = get_decorated_method_info(MockClass, "test_method")
        self.assertTrue(info["exists"])
        self.assertTrue(info["is_callable"])
        self.assertFalse(info["is_decorated"])  # Not decorated yet

    @patch("src.log_aggregator.automatic_decorator_application.logger")
    def test_apply_automatic_decorators_logging(self, mock_logger):
        """Test that automatic decorator application logs properly."""
        with patch.object(self.applicator, "apply_automatic_decoration") as mock_apply:
            mock_apply.return_value = {"TestClass": ["test_method"]}

            result = apply_automatic_decorators()

            # Should return the decoration summary
            self.assertEqual(result, {"TestClass": ["test_method"]})

            # Should have logged the process
            mock_logger.info.assert_called()

    def test_operation_type_coverage(self):
        """Test that all important OperationType values are covered."""
        mapping = self.applicator.operation_method_mapping

        # Get all operation types from mapping
        mapped_operations = set(mapping.keys())

        # Check that we cover the most important operations
        important_operations = {
            OperationType.ADD_REACTION,
            OperationType.REMOVE_REACTION,
            OperationType.HIGHLIGHT_REACTION,
            OperationType.UPDATE_VALUE,
            OperationType.DECONVOLUTION,
            OperationType.LOAD_FILE,
            OperationType.RESET_FILE_DATA,
            OperationType.ADD_NEW_SERIES,
            OperationType.DELETE_SERIES,
            OperationType.MODEL_FIT_CALCULATION,
            OperationType.MODEL_FREE_CALCULATION,
            OperationType.MODEL_BASED_CALCULATION,
        }

        missing_operations = important_operations - mapped_operations
        self.assertEqual(len(missing_operations), 0, f"Missing mappings for operations: {missing_operations}")

    def test_report_generation(self):
        """Test decoration report generation."""
        # Mock some decoration data
        self.applicator.decoration_summary = {"TestClass1": ["method1", "method2"], "TestClass2": ["method3"]}
        self.applicator.decorated_classes = {"TestClass1", "TestClass2"}

        report = self.applicator.generate_decoration_report()

        # Report should contain expected sections
        self.assertIn("AUTOMATIC DECORATOR APPLICATION REPORT", report)
        self.assertIn("DECORATED CLASSES AND METHODS", report)
        self.assertIn("TestClass1: 2 methods", report)
        self.assertIn("TestClass2: 1 methods", report)

    def test_disabled_decoration(self):
        """Test behavior when automatic decoration is disabled."""
        with patch.object(AutoDecorationConfig, "ENABLED", False):
            result = apply_automatic_decorators()

            # Should return empty dict when disabled
            self.assertEqual(result, {})


class TestStage6Integration(unittest.TestCase):
    """Integration tests for Stage 6 functionality."""

    def test_real_baseslots_classes_detection(self):
        """Test detection of real BaseSlots classes in the project."""
        try:
            from src.core.base_signals import BaseSlots

            applicator = AutomaticDecoratorApplicator()
            subclasses = applicator._get_all_baseslots_subclasses(BaseSlots)

            # Should find real classes
            subclass_names = {cls.__name__ for cls in subclasses}

            logger.info(f"Found BaseSlots subclasses: {subclass_names}")

            # Verify we found some expected classes
            expected_minimum = {"CalculationsDataOperations", "FileData", "SeriesData"}
            found_expected = expected_minimum.intersection(subclass_names)

            self.assertGreaterEqual(
                len(found_expected), 2, f"Expected to find at least 2 of {expected_minimum}, found {found_expected}"
            )

        except ImportError as e:
            self.skipTest(f"Cannot test real classes: {e}")

    def test_operation_type_enum_consistency(self):
        """Test that OperationType enum is consistent with mappings."""
        from src.core.app_settings import OperationType

        applicator = AutomaticDecoratorApplicator()
        mapping = applicator.operation_method_mapping

        # Get all OperationType values
        all_operations = set(OperationType)
        mapped_operations = set(mapping.keys())

        # Calculate coverage
        coverage_percentage = len(mapped_operations) / len(all_operations) * 100

        logger.info(
            f"Operation mapping coverage: {coverage_percentage:.1f}% "
            f"({len(mapped_operations)}/{len(all_operations)})"
        )

        # Should have reasonable coverage (at least 70%)
        self.assertGreaterEqual(coverage_percentage, 70.0, "Operation mapping coverage too low")


def run_stage_6_tests():
    """Run all Stage 6 tests."""
    logger.info("=" * 60)
    logger.info("RUNNING STAGE 6 TESTS")
    logger.info("=" * 60)

    # Create test suite
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTest(unittest.makeSuite(TestStage6AutomaticDecoration))
    suite.addTest(unittest.makeSuite(TestStage6Integration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Report results
    logger.info("\nTest Results:")
    logger.info(f"Tests run: {result.testsRun}")
    logger.info(f"Failures: {len(result.failures)}")
    logger.info(f"Errors: {len(result.errors)}")

    if result.failures:
        logger.error("Test Failures:")
        for test, failure in result.failures:
            logger.error(f"  {test}: {failure}")

    if result.errors:
        logger.error("Test Errors:")
        for test, error in result.errors:
            logger.error(f"  {test}: {error}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        logger.info("✅ All Stage 6 tests passed!")
    else:
        logger.error("❌ Some Stage 6 tests failed!")

    return success


if __name__ == "__main__":
    # Run the tests
    success = run_stage_6_tests()

    if not success:
        exit(1)
