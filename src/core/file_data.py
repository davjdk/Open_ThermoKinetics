import os
from functools import wraps
from io import StringIO

import chardet
import pandas as pd
from core.logger_config import logger
from core.logger_console import LoggerConsole as console
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


def detect_encoding(func):
    def wrapper(self, *args, **kwargs):
        with open(self.file_path, "rb") as f:
            result = chardet.detect(f.read(100_000))
        kwargs["encoding"] = result["encoding"]
        return func(self, *args, **kwargs)

    return wrapper


def detect_decimal(func):
    @wraps(func)
    def wrapper(self, **kwargs):
        encoding = kwargs.get("encoding", "utf-8")
        with open(self.file_path, "r", encoding=encoding) as f:
            sample_lines = [next(f) for _ in range(100)]
        sample_text = "".join(sample_lines)
        # Простая эвристика: если запятых больше, чем точек, предполагаем,
        # что запятая используется как десятичный разделитель
        decimal_sep = "," if sample_text.count(",") > sample_text.count(".") else "."
        kwargs["decimal"] = decimal_sep
        return func(self, **kwargs)

    return wrapper


class FileData(QObject):
    response_signal = pyqtSignal(dict)
    data_loaded_signal = pyqtSignal(pd.DataFrame)
    plot_dataframe_signal = pyqtSignal(pd.DataFrame)

    def __init__(self):
        super().__init__()
        self.data = None
        self.original_data = {}
        self.dataframe_copies = {}
        self.file_path = None
        self.delimiter = ","
        self.skip_rows = 0
        self.columns_names = None
        self.operations_history = {}
        self.loaded_files = set()

    def log_operation(self, params: dict):
        file_name = params.pop("file_name")
        if file_name not in self.operations_history:
            self.operations_history[file_name] = []
        self.operations_history[file_name].append(
            {
                "params": params,
            }
        )
        logger.debug(f"История операций: {self.operations_history}")

    def check_operation_executed(self, file_name: str, operation: str):
        if file_name in self.operations_history:
            for operation_record in self.operations_history[file_name]:
                if operation_record["params"]["operation"] == operation:
                    return True
        return False

    @pyqtSlot(tuple)
    def load_file(self, file_info):
        self.file_path, self.delimiter, self.skip_rows, columns_names = file_info

        if self.file_path in self.loaded_files:
            console.log(f"Файл: {self.file_path} уже загружен.")
            return

        if columns_names:
            column_delimiter = "," if "," in columns_names else " "
            self.columns_names = [name.strip() for name in columns_names.split(column_delimiter)]
            logger.debug(
                "Загружен файл: путь=%s, разделитель=%s, пропуск строк=%s, имена столбцов=%s",
                self.file_path,
                self.delimiter,
                self.skip_rows,
                columns_names,
            )
        else:
            logger.debug(
                "Загружен файл: путь=%s, разделитель=%s, пропуск строк=%s, имена столбцов=нет (пустая строка)",
                self.file_path,
                self.delimiter,
                self.skip_rows,
            )

        _, file_extension = os.path.splitext(self.file_path)
        if file_extension == ".csv":
            self.load_csv()
        elif file_extension == ".txt":
            self.load_txt()

        self.loaded_files.add(self.file_path)

    @detect_encoding
    @detect_decimal
    def load_csv(self, **kwargs):
        try:
            self.data = pd.read_csv(
                self.file_path,
                sep=self.delimiter,
                engine="python",
                on_bad_lines="skip",
                skiprows=self.skip_rows,
                header=0,
                **kwargs,
            )
            self._fetch_data()
        except Exception as e:
            logger.error("Ошибка при загрузке CSV файла: %s", e)

    @detect_encoding
    @detect_decimal
    def load_txt(self, **kwargs):
        try:
            self.data = pd.read_table(
                self.file_path,
                sep=self.delimiter,
                skiprows=self.skip_rows,
                header=0,
                **kwargs,
            )
            self._fetch_data()
        except Exception as e:
            logger.error("Ошибка при загрузке TXT файла: %s", e)

    def _fetch_data(self):
        file_basename = os.path.basename(self.file_path)

        if self.columns_names is not None:
            if len(self.columns_names) != len(self.data.columns):
                logger.warning("Количество имен столбцов не соответствует количеству столбцов в данных.")
            self.data = self.data.apply(pd.to_numeric, errors="coerce")
            self.data.columns = [name.strip() for name in self.columns_names]
        else:
            logger.debug("Первая строка оставлена как имена столбцов: %s", self.data.columns)

        self.original_data[file_basename] = self.data.copy()
        self.dataframe_copies[file_basename] = self.data.copy()
        buffer = StringIO()
        self.dataframe_copies[file_basename].info(buf=buffer)
        file_info = buffer.getvalue()
        console.log(f"Загружен файл:\n {file_info}")
        logger.debug(f"Ключи dataframe_copies: {self.dataframe_copies.keys()}")
        self.data_loaded_signal.emit(self.data)

    @pyqtSlot(str)
    def plot_dataframe_copy(self, key):
        if key in self.dataframe_copies:
            self.plot_dataframe_signal.emit(self.dataframe_copies[key])
        else:
            logger.error(f"Ключ {key} не найден в dataframe_copies.")

    def reset_dataframe_copy(self, key):
        if key in self.original_data:
            self.dataframe_copies[key] = self.original_data[key].copy()
            self.plot_dataframe_signal.emit(self.dataframe_copies[key])
            if key in self.operations_history:
                del self.operations_history[key]
                logger.debug(f"История операций: {self.operations_history}")

    def modify_data(self, func, params):
        file_name = params.get("file_name")
        if not callable(func):
            logger.error("Предоставленный аргумент не является функцией")
            return

        if file_name not in self.dataframe_copies:
            logger.error(f"Ключ {file_name} не найден в dataframe_copies.")
            return

        try:
            dataframe = self.dataframe_copies[file_name]
            for column in dataframe.columns:
                if column != "temperature":
                    dataframe[column] = func(dataframe[column])

            self.log_operation(params)
            self.plot_dataframe_signal.emit(self.dataframe_copies[file_name])
            logger.info("Данные были успешно модифицированы.")

        except Exception as e:
            logger.error(f"Ошибка при модификации данных файла:{file_name}: {e}")

    @pyqtSlot(dict)
    def request_slot(self, params: dict):
        if params["target"] != "file_data":
            return

        logger.debug(f"В handle_request пришли данные {params}")
        operation, file_name, func = params.get("operation"), params.get("file_name", None), params.get("function")

        if operation == "differential":
            if not self.check_operation_executed(file_name, "differential"):
                self.modify_data(func, params)
            else:
                console.log("Данные уже приведены к da/dT")
        elif operation == "check_differential":
            params["data"] = self.check_operation_executed(file_name, "differential")
        elif operation == "get_df_data":
            params["data"] = self.dataframe_copies[file_name]
        elif operation == "reset":
            self.reset_dataframe_copy(file_name)
            params["data"] = True
        elif operation == "plot_dataframe":
            self.plot_dataframe_signal.emit(self.dataframe_copies[file_name])
            params["data"] = True
        else:
            return

        params["target"], params["actor"] = params["actor"], params["target"]
        self.response_signal.emit(params)
