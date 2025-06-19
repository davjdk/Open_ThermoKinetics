"""
Model Calculation Proxy Module

This module provides a proxy manager for controlling model-based calculation worker processes
from the main GUI thread. It handles process lifecycle, result monitoring through QTimer,
and integration with Qt signals system.

Author: Assistant
Date: 2025
"""

import multiprocessing
from typing import Any, Dict, Optional, Union

from PyQt6.QtCore import QObject, QTimer

from src.core.logger_config import LoggerManager
from src.core.model_calc_worker import run_model_calc

logger = LoggerManager.get_logger(__name__)


class ModelCalcProxy(QObject):
    """
    Proxy manager for controlling model-based calculation worker processes.

    This class manages the lifecycle of worker processes, monitors results through
    QTimer, and integrates with Qt signals for communication with the main application.

    Responsibilities:
    - Start and stop worker processes
    - Monitor result queue through QTimer
    - Handle process completion and errors
    - Integrate with Qt signal system
    - Manage resource cleanup
    """

    def __init__(self, calculations_obj):
        """
        Initialize the proxy manager.

        Args:
            calculations_obj: Calculations instance for signal emission and stop_event access
        """
        super().__init__()
        self.calculations = calculations_obj
        self.process: Optional[multiprocessing.Process] = None
        self.queue: Optional[multiprocessing.Queue] = None
        self.timer: Optional[QTimer] = None
        self._is_stopping = False

        logger.debug("ModelCalcProxy initialized")

    def start_process(self, target_func_data: Dict[str, Any], bounds: list, method_params: Dict[str, Any]) -> bool:
        """
        Start worker process for model-based calculation.

        Args:
            target_func_data: Serialized target function data from recreate_target_function_data
            bounds: Parameter bounds for optimization [(min, max), ...]
            method_params: Differential evolution algorithm parameters

        Returns:
            bool: True if process started successfully, False otherwise
        """
        try:
            # Clean up any existing process
            if self.process and self.process.is_alive():
                logger.warning("Stopping existing process before starting new one")
                self.stop_process()

            # Reset stopping flag
            self._is_stopping = False

            # Prepare inter-process communication
            self.calculations.stop_event.clear()
            self.queue = multiprocessing.Queue()

            # Create and start process
            self.process = multiprocessing.Process(
                target=run_model_calc,
                args=(target_func_data, bounds, method_params, self.calculations.stop_event, self.queue),
            )
            self.process.start()

            # Start result monitoring
            self._start_queue_monitoring()

            logger.info(f"Model calculation process started (PID: {self.process.pid})")
            return True

        except Exception as e:
            logger.error(f"Failed to start model calculation process: {e}")
            self._cleanup_resources()
            return False

    def _start_queue_monitoring(self):
        """Start QTimer for monitoring result queue."""
        if self.timer:
            self.timer.stop()

        self.timer = QTimer()
        self.timer.setInterval(100)  # Check every 100ms
        self.timer.timeout.connect(self._poll_queue)
        self.timer.start()

        logger.debug("Queue monitoring started")

    def _poll_queue(self):
        """Poll result queue and handle messages."""
        if not self.queue:
            return

        # Process all available messages
        messages_processed = 0
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                self._handle_message(msg)
                messages_processed += 1

                # Limit messages processed per poll to avoid GUI freezing
                if messages_processed >= 10:
                    break

            except Exception as e:
                logger.debug(f"Queue polling error (expected if empty): {e}")
                break

        # Check process state
        if self.process and not self.process.is_alive():
            self._handle_process_finished()

    def _handle_message(self, msg: Dict[str, Any]):
        """
        Handle individual message from worker process.

        Args:
            msg: Message dictionary from worker
        """
        try:
            if not isinstance(msg, dict):
                logger.warning(f"Received non-dict message: {type(msg)}")
                return

            msg_type = msg.get("type", "unknown")

            if msg_type == "intermediate_result":
                # Intermediate optimization result
                if "best_mse" in msg and "best_params" in msg:
                    self.calculations.new_best_result.emit(msg)
                    logger.debug(f"Emitted intermediate result with MSE: {msg.get('best_mse', 'N/A')}")

            elif msg_type == "final_result":
                # Final optimization result
                result_data = msg.get("result")
                if result_data:
                    logger.info("Received final calculation result")
                    self._finish_process(result_data)
                else:
                    logger.error("Final result message missing result data")
                    self._finish_process(Exception("Invalid final result"))

            elif msg_type == "error":
                # Error in worker process
                error_msg = msg.get("error", "Unknown worker error")
                logger.error(f"Worker process error: {error_msg}")
                self._finish_process(Exception(error_msg))

            elif msg_type == "progress":
                # Progress update (for future use)
                progress = msg.get("progress", 0)
                logger.debug(f"Calculation progress: {progress}%")

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling worker message: {e}")

    def _handle_process_finished(self):
        """Handle worker process completion without final message."""
        if self._is_stopping:
            # Expected termination
            logger.info("Worker process stopped as requested")
            self._finish_process(Exception("Calculation stopped by user"))
        else:
            # Unexpected termination
            exit_code = self.process.exitcode if self.process else -1
            logger.warning(f"Worker process finished unexpectedly (exit code: {exit_code})")

            if exit_code != 0:
                self._finish_process(Exception(f"Process terminated with exit code {exit_code}"))
            else:
                self._finish_process(Exception("Process finished without result"))

    def _finish_process(self, result_obj: Union[Any, Exception]):
        """
        Complete process cleanup and notify Calculations.

        Args:
            result_obj: Optimization result or Exception object
        """
        logger.debug(f"Finishing process with result type: {type(result_obj).__name__}")

        # Stop monitoring
        if self.timer:
            self.timer.stop()
            self.timer = None

        # Cleanup process
        self._cleanup_process()

        # Clear queue
        self._cleanup_queue()

        # Notify calculations of completion
        if hasattr(self.calculations, "_calculation_finished"):
            self.calculations._calculation_finished(result_obj)
        else:
            logger.warning("Calculations object missing _calculation_finished method")

    def stop_process(self) -> bool:
        """
        Stop currently running worker process.

        Returns:
            bool: True if process was stopped, False if no active process
        """
        if not self.process or not self.process.is_alive():
            logger.debug("No active process to stop")
            return False

        self._is_stopping = True

        try:
            # Set stop flag for graceful shutdown
            self.calculations.stop_event.set()
            logger.info("Stop signal sent to worker process")

            # Schedule forced termination as backup
            QTimer.singleShot(2000, self._force_terminate)  # 2 seconds timeout

            return True

        except Exception as e:
            logger.error(f"Error stopping process: {e}")
            self._force_terminate()
            return False

    def _force_terminate(self):
        """Force termination of worker process if graceful stop failed."""
        if self.process and self.process.is_alive():
            logger.warning("Force terminating worker process")
            try:
                self.process.terminate()
                self.process.join(timeout=1.0)

                if self.process.is_alive():
                    logger.error("Process still alive after terminate, using kill")
                    self.process.kill()

            except Exception as e:
                logger.error(f"Error during force termination: {e}")

    def _cleanup_process(self):
        """Clean up process resources."""
        if self.process:
            try:
                if self.process.is_alive():
                    self.process.terminate()
                self.process.join(timeout=1.0)

                if self.process.is_alive():
                    self.process.kill()

            except Exception as e:
                logger.error(f"Error during process cleanup: {e}")
            finally:
                self.process = None

    def _cleanup_queue(self):
        """Clean up queue resources."""
        if self.queue:
            try:
                # Drain remaining messages
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                    except Exception:
                        break

                self.queue.close()
                self.queue.join_thread()

            except Exception as e:
                logger.error(f"Error during queue cleanup: {e}")
            finally:
                self.queue = None

    def _cleanup_resources(self):
        """Complete cleanup of all resources."""
        self._cleanup_process()
        self._cleanup_queue()

        if self.timer:
            self.timer.stop()
            self.timer = None

    def is_running(self) -> bool:
        """
        Check if worker process is currently running.

        Returns:
            bool: True if process is active, False otherwise
        """
        return self.process is not None and self.process.is_alive()

    def get_process_info(self) -> Dict[str, Any]:
        """
        Get information about current process state.

        Returns:
            dict: Process information including PID, status, etc.
        """
        if not self.process:
            return {"status": "no_process", "pid": None, "alive": False}

        return {
            "status": "running" if self.process.is_alive() else "finished",
            "pid": self.process.pid,
            "alive": self.process.is_alive(),
            "exitcode": getattr(self.process, "exitcode", None),
            "monitoring": self.timer is not None and self.timer.isActive(),
        }

    def __del__(self):
        """Destructor to ensure resource cleanup."""
        try:
            self._cleanup_resources()
        except Exception as e:
            logger.error(f"Error during ModelCalcProxy destruction: {e}")
