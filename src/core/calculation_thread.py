from PyQt6.QtCore import QThread, pyqtSignal

from src.core.logger_config import logger


class CalculationThread(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, calculation_func, *args, **kwargs):
        super().__init__()
        self.calculation_func = calculation_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        logger.info("CalculationThread.run() started")
        try:
            result = self.calculation_func(*self.args, **self.kwargs)
            logger.info(f"CalculationThread.run() completed with result: {type(result)}")
        except Exception as e:
            logger.error(f"Error during calculation: {e}")
            result = e

        logger.info(f"CalculationThread.run() emitting result_ready signal with result: {type(result)}")
        self.result_ready.emit(result)
        logger.info("CalculationThread.run() finished")
