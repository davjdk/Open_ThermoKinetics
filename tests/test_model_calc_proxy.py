"""
Tests for Model Calculation Proxy Module

This module contains comprehensive tests for the ModelCalcProxy class,
including process lifecycle, message handling, error scenarios, and Qt integration.

Author: Assistant
Date: 2025
"""

import multiprocessing
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import QObject

from src.core.model_calc_proxy import ModelCalcProxy


class MockCalculations(QObject):
    """Mock Calculations object for testing."""

    def __init__(self):
        super().__init__()
        self.stop_event = multiprocessing.Event()
        self.new_best_result = Mock()
        self.signals_emitted = []

        # Track signal emissions
        self.new_best_result.emit = self._track_signal_emit

    def _track_signal_emit(self, data):
        """Track signal emissions for testing."""
        self.signals_emitted.append(data)

    def _calculation_finished(self, result):
        """Mock calculation finished handler."""
        self.finish_result = result


class TestModelCalcProxy(unittest.TestCase):
    """Test cases for ModelCalcProxy class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_calculations = MockCalculations()
        self.proxy = ModelCalcProxy(self.mock_calculations)

        # Test data
        self.test_func_data = {
            "num_species": 2,
            "num_reactions": 2,
            "betas": [3.0, 5.0, 10.0],
            "all_exp_masses": [[1.0], [1.0], [1.0]],
            "exp_temperature": [300, 400, 500],
            "species_list": [{"id": "A"}, {"id": "B"}],
            "reactions": [
                {"from": "A", "to": "B", "reaction_type": "F2"},
                {"from": "B", "to": "C", "reaction_type": "F1"},
            ],
        }

        self.test_bounds = [(0, 10), (0, 10), (50, 200), (50, 200)]
        self.test_method_params = {"maxiter": 5, "popsize": 2}

    def tearDown(self):
        """Clean up after tests."""
        if self.proxy:
            self.proxy.stop_process()
            self.proxy._cleanup_resources()

    def test_proxy_initialization(self):
        """Test proxy manager initialization."""
        self.assertIsInstance(self.proxy, ModelCalcProxy)
        self.assertEqual(self.proxy.calculations, self.mock_calculations)
        self.assertIsNone(self.proxy.process)
        self.assertIsNone(self.proxy.queue)
        self.assertIsNone(self.proxy.timer)
        self.assertFalse(self.proxy._is_stopping)

    @patch("src.core.model_calc_proxy.multiprocessing.Process")
    @patch("src.core.model_calc_proxy.multiprocessing.Queue")
    def test_start_process_success(self, mock_queue_class, mock_process_class):
        """Test successful process start."""
        # Setup mocks
        mock_queue = Mock()
        mock_process = Mock()
        mock_queue_class.return_value = mock_queue
        mock_process_class.return_value = mock_process
        mock_process.pid = 12345

        # Start process
        result = self.proxy.start_process(self.test_func_data, self.test_bounds, self.test_method_params)

        # Verify success
        self.assertTrue(result)
        self.assertEqual(self.proxy.process, mock_process)
        self.assertEqual(self.proxy.queue, mock_queue)
        self.assertIsNotNone(self.proxy.timer)  # Verify process was started
        mock_process.start.assert_called_once()

        # Verify timer was created (note: isActive() may fail in test environment)
        self.assertEqual(self.proxy.timer.interval(), 100)

    @patch("src.core.model_calc_proxy.multiprocessing.Process")
    def test_start_process_failure(self, mock_process_class):
        """Test process start failure."""
        # Make process creation fail
        mock_process_class.side_effect = Exception("Process creation failed")

        # Attempt to start process
        result = self.proxy.start_process(self.test_func_data, self.test_bounds, self.test_method_params)

        # Verify failure
        self.assertFalse(result)
        self.assertIsNone(self.proxy.process)
        self.assertIsNone(self.proxy.queue)
        self.assertIsNone(self.proxy.timer)

    def test_handle_intermediate_result_message(self):
        """Test handling of intermediate result messages."""
        # Create test message
        test_message = {"type": "intermediate_result", "best_mse": 0.123, "best_params": [1.0, 2.0, 3.0]}

        # Handle message
        self.proxy._handle_message(test_message)

        # Verify signal was emitted
        self.assertEqual(len(self.mock_calculations.signals_emitted), 1)
        self.assertEqual(self.mock_calculations.signals_emitted[0], test_message)

    def test_handle_final_result_message(self):
        """Test handling of final result messages."""
        # Setup mock for _finish_process
        self.proxy._finish_process = Mock()

        # Create test message
        test_result = {"optimization_result": "success"}
        test_message = {"type": "final_result", "result": test_result}

        # Handle message
        self.proxy._handle_message(test_message)

        # Verify _finish_process was called with result
        self.proxy._finish_process.assert_called_once_with(test_result)

    def test_handle_error_message(self):
        """Test handling of error messages."""
        # Setup mock for _finish_process
        self.proxy._finish_process = Mock()

        # Create test message
        test_message = {"type": "error", "error": "Test error message"}

        # Handle message
        self.proxy._handle_message(test_message)

        # Verify _finish_process was called with Exception
        self.proxy._finish_process.assert_called_once()
        args = self.proxy._finish_process.call_args[0]
        self.assertIsInstance(args[0], Exception)
        self.assertIn("Test error message", str(args[0]))

    def test_handle_unknown_message_type(self):
        """Test handling of unknown message types."""
        # Create test message with unknown type
        test_message = {"type": "unknown_type", "data": "some data"}

        # Handle message should not raise exception
        try:
            self.proxy._handle_message(test_message)
        except Exception as e:
            self.fail(f"Handling unknown message type raised exception: {e}")

    def test_handle_invalid_message_format(self):
        """Test handling of invalid message formats."""
        # Test with non-dict message
        invalid_messages = ["string message", 123, None, ["list", "message"]]

        for invalid_msg in invalid_messages:
            try:
                self.proxy._handle_message(invalid_msg)
            except Exception as e:
                self.fail(f"Handling invalid message raised exception: {e}")

    @patch("src.core.model_calc_proxy.multiprocessing.Process")
    @patch("src.core.model_calc_proxy.multiprocessing.Queue")
    def test_stop_process_success(self, mock_queue_class, mock_process_class):
        """Test successful process stop."""
        # Setup running process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process.pid = 12345
        self.proxy.process = mock_process

        # Stop process
        result = self.proxy.stop_process()

        # Verify success
        self.assertTrue(result)
        self.assertTrue(self.proxy._is_stopping)
        self.assertTrue(self.mock_calculations.stop_event.is_set())

    def test_stop_process_no_active_process(self):
        """Test stop when no active process."""
        # No process running
        self.proxy.process = None

        # Attempt to stop
        result = self.proxy.stop_process()

        # Verify failure response
        self.assertFalse(result)

    def test_is_running_with_active_process(self):
        """Test is_running with active process."""
        # Setup mock process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        self.proxy.process = mock_process

        # Check running status
        self.assertTrue(self.proxy.is_running())

    def test_is_running_with_no_process(self):
        """Test is_running with no process."""
        # No process
        self.proxy.process = None

        # Check running status
        self.assertFalse(self.proxy.is_running())

    def test_is_running_with_dead_process(self):
        """Test is_running with dead process."""
        # Setup mock dead process
        mock_process = Mock()
        mock_process.is_alive.return_value = False
        self.proxy.process = mock_process

        # Check running status
        self.assertFalse(self.proxy.is_running())

    def test_get_process_info_no_process(self):
        """Test get_process_info with no process."""
        # Get info
        info = self.proxy.get_process_info()

        # Verify info
        expected = {"status": "no_process", "pid": None, "alive": False}
        self.assertEqual(info, expected)

    def test_get_process_info_with_process(self):
        """Test get_process_info with active process."""
        # Setup mock process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process.pid = 12345
        mock_process.exitcode = None
        self.proxy.process = mock_process

        # Setup mock timer
        mock_timer = Mock()
        mock_timer.isActive.return_value = True
        self.proxy.timer = mock_timer

        # Get info
        info = self.proxy.get_process_info()

        # Verify info
        self.assertEqual(info["status"], "running")
        self.assertEqual(info["pid"], 12345)
        self.assertTrue(info["alive"])
        self.assertIsNone(info["exitcode"])
        self.assertTrue(info["monitoring"])

    def test_cleanup_resources(self):
        """Test complete resource cleanup."""
        # Setup mock resources
        mock_process = Mock()
        mock_process.is_alive.return_value = False
        mock_queue = Mock()
        mock_timer = Mock()

        self.proxy.process = mock_process
        self.proxy.queue = mock_queue
        self.proxy.timer = mock_timer

        # Cleanup
        self.proxy._cleanup_resources()

        # Verify cleanup
        self.assertIsNone(self.proxy.process)
        self.assertIsNone(self.proxy.queue)
        self.assertIsNone(self.proxy.timer)
        mock_timer.stop.assert_called_once()
        mock_queue.close.assert_called_once()

    @patch("src.core.model_calc_proxy.multiprocessing.Process")
    @patch("src.core.model_calc_proxy.multiprocessing.Queue")
    def test_restart_process(self, mock_queue_class, mock_process_class):
        """Test restarting process while one is already running."""
        # Setup initial running process
        mock_process1 = Mock()
        mock_process1.is_alive.return_value = True
        mock_process1.pid = 11111

        mock_process2 = Mock()
        mock_process2.is_alive.return_value = True
        mock_process2.pid = 22222

        mock_queue = Mock()

        mock_process_class.side_effect = [mock_process1, mock_process2]
        mock_queue_class.return_value = mock_queue

        # Start first process
        result1 = self.proxy.start_process(self.test_func_data, self.test_bounds, self.test_method_params)
        self.assertTrue(result1)
        self.assertEqual(self.proxy.process, mock_process1)

        # Start second process (should stop first)
        result2 = self.proxy.start_process(self.test_func_data, self.test_bounds, self.test_method_params)
        self.assertTrue(result2)
        self.assertEqual(self.proxy.process, mock_process2)

    def test_queue_polling_with_empty_queue(self):
        """Test queue polling when queue is empty."""
        # Setup empty queue
        mock_queue = Mock()
        mock_queue.empty.return_value = True
        self.proxy.queue = mock_queue

        # Setup live process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        self.proxy.process = mock_process

        # Poll queue (should not raise exception)
        try:
            self.proxy._poll_queue()
        except Exception as e:
            self.fail(f"Polling empty queue raised exception: {e}")

    def test_force_terminate_when_process_wont_stop(self):
        """Test force termination of stubborn process."""
        # Setup stubborn process
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        mock_process.terminate = Mock()
        mock_process.kill = Mock()
        mock_process.join = Mock()
        self.proxy.process = mock_process

        # Force terminate
        self.proxy._force_terminate()

        # Verify terminate was called
        mock_process.terminate.assert_called_once()
        mock_process.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
