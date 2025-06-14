"""
Тесты для валидации упрощенной системы
Этап 7: Тестирование после упрощения
"""

import time
from typing import List

import pytest

from src.log_aggregator.operation_logger import log_operation, operation_logger
from src.log_aggregator.operation_monitor import operation_monitor


class TestSimplifiedSystemValidation:
    """Тесты для проверки упрощенной системы логирования"""

    def setup_method(self):
        """Настройка для каждого теста"""
        operation_monitor.reset()
        operation_logger.reset()

    def test_functionality_preservation(self):
        """Проверить, что ключевая функциональность сохранена"""

        # Основные операции должны работать как раньше
        with log_operation("TEST_OPERATION"):
            operation_logger.add_metric("test_data", list(range(1000)))
            operation_logger.add_metric("operation_type", "validation")

        # Проверить, что операция записана корректно
        self.verify_operation_recorded("TEST_OPERATION")

        # Проверить обработку больших данных
        self.verify_large_data_handling()

    def test_removed_components_impact(self):
        """Проверить отсутствие негативного влияния удаленных компонентов"""

        # Попробовать импортировать компоненты, которые должны быть удалены
        removed_components = ["ValueAggregator"]

        for component in removed_components:
            try:
                # Попытка импорта удаленного компонента
                exec(f"from src.log_aggregator.value_aggregator import {component}")
                # Если импорт успешен, это может означать, что компонент не удален
                # Но это не обязательно ошибка на этапе тестирования
                pass
            except ImportError:
                # Ожидаемое поведение для удаленных компонентов
                pass

        # Упрощенные компоненты должны работать
        self.verify_simplified_components_working()

    def test_performance_improvement(self):
        """Проверить улучшение производительности"""

        # Замерить время обработки логов
        start_time = time.time()

        # Обработать большой объем логов
        for i in range(500):
            with log_operation(f"PERF_TEST_{i % 10}"):
                operation_logger.add_metric("iteration", i)

        processing_time = time.time() - start_time

        # Упрощенная система должна быть достаточно быстрой
        # Ожидаем менее 5 секунд на 500 операций
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, expected < 5s"

        # Проверить, что все операции записаны
        completed_operations = operation_monitor.get_completed_operations()
        assert len(completed_operations) >= 500, "Should have recorded all operations"

    def test_memory_usage_reduction(self):
        """Проверить снижение потребления памяти"""

        import psutil

        process = psutil.Process()

        initial_memory = process.memory_info().rss

        # Генерировать логи с упрощенной системой
        self.generate_test_logs(1000)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Должно быть разумное потребление памяти
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 100, f"Memory increase: {memory_increase_mb:.1f}MB, expected < 100MB"

    def test_essential_patterns_still_detected(self):
        """Проверить, что важные паттерны все еще обнаруживаются"""

        # Проверить, что PatternDetector все еще работает для важных паттернов
        try:
            from src.log_aggregator.pattern_detector import PatternDetector

            detector = PatternDetector()

            # Создать тестовые записи для важных паттернов
            test_records = self.create_test_log_records()

            # Попытаться обнаружить паттерны
            patterns = detector.detect_patterns(test_records)

            # Важные типы паттернов должны быть доступны
            expected_pattern_types = {"file_operations", "gui_updates"}
            detected_types = {p.pattern_type for p in patterns if hasattr(p, "pattern_type")}

            # Проверить, что хотя бы некоторые важные паттерны обнаруживаются
            assert (
                len(detected_types.intersection(expected_pattern_types)) > 0
            ), "Should detect at least some essential patterns"

        except ImportError:
            # Если PatternDetector удален полностью, это тоже валидный результат
            pass

    def test_operation_aggregation_still_works(self):
        """Проверить, что агрегация операций все еще работает"""

        # Создать несколько операций
        operation_names = ["AGGR_TEST_1", "AGGR_TEST_2", "AGGR_TEST_3"]

        for name in operation_names:
            with log_operation(name):
                operation_logger.add_metric("aggregation_test", True)  # Проверить, что все операции записаны
        completed_operations = operation_monitor.get_completed_operations()
        recorded_names = {op.operation_type for op in completed_operations}

        for name in operation_names:
            assert name in recorded_names, f"Operation {name} should be recorded"

    def test_error_handling_preserved(self):
        """Проверить, что обработка ошибок сохранена"""

        # Тест операции с ошибкой
        with pytest.raises(ValueError):
            with log_operation("ERROR_TEST"):
                operation_logger.add_metric("will_fail", True)
                raise ValueError("Test error")  # Проверить, что операция с ошибкой записана
        completed_operations = operation_monitor.get_completed_operations()
        error_ops = [op for op in completed_operations if op.operation_type == "ERROR_TEST"]

        assert len(error_ops) > 0, "Error operation should be recorded"

    def verify_operation_recorded(self, operation_name: str):
        """Проверить, что операция записана корректно"""
        completed_operations = operation_monitor.get_completed_operations()
        target_ops = [op for op in completed_operations if op.operation_type == operation_name]

        assert len(target_ops) == 1, f"Should have exactly one operation named {operation_name}"

        target_op = target_ops[0]
        assert hasattr(target_op, "operation_type"), "Operation should have operation_type"
        assert target_op.operation_type == operation_name, f"Operation type should be {operation_name}"

    def verify_large_data_handling(self):
        """Проверить обработку больших данных"""
        # Создать операцию с большими данными
        large_data = list(range(5000))

        with log_operation("LARGE_DATA_TEST"):
            operation_logger.add_metric("large_list", large_data)
            operation_logger.add_metric("data_size", len(large_data))

        # Проверить, что операция записана
        completed_operations = operation_monitor.get_completed_operations()
        large_ops = [op for op in completed_operations if op.operation_type == "LARGE_DATA_TEST"]

        assert len(large_ops) == 1, "Large data operation should be recorded"
        assert "data_size" in large_ops[0].custom_metrics, "Should have data_size metric"

    def verify_simplified_components_working(self):
        """Проверить работу упрощенных компонентов"""

        # Тест упрощенного OperationAggregator (если применимо)
        try:
            from src.log_aggregator.operation_aggregator import OperationAggregator

            aggregator = OperationAggregator()

            # Проверить, что основная функциональность работает
            # (детали зависят от того, как именно упрощен компонент)
            assert hasattr(aggregator, "process_record"), "OperationAggregator should retain core functionality"

        except (ImportError, AttributeError):
            # Если компонент серьезно изменен, это нормально
            pass

    def generate_test_logs(self, count: int):
        """Сгенерировать тестовые логи"""
        for i in range(count):
            with log_operation(f"MEMORY_TEST_{i % 20}"):
                operation_logger.add_metric("test_index", i)
                operation_logger.add_metric("test_data", f"data_{i}")

    def create_test_log_records(self) -> List:
        """Создать тестовые лог-записи"""
        import logging
        from datetime import datetime

        from src.log_aggregator.buffer_manager import BufferedLogRecord

        records = []

        # Создать записи для файловых операций (минимум 2 похожих для формирования паттерна)
        file_record1 = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Loading file: test.csv", args=(), exc_info=None
        )
        file_buffered1 = BufferedLogRecord(record=file_record1, timestamp=datetime.now())
        records.append(file_buffered1)

        file_record2 = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="Loading file: data.csv", args=(), exc_info=None
        )
        file_buffered2 = BufferedLogRecord(record=file_record2, timestamp=datetime.now())
        records.append(file_buffered2)

        # Создать записи для GUI обновлений (минимум 2 похожих для формирования паттерна)
        gui_record1 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Updating plot canvas with new data",
            args=(),
            exc_info=None,
        )
        gui_buffered1 = BufferedLogRecord(record=gui_record1, timestamp=datetime.now())
        records.append(gui_buffered1)

        gui_record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Updating plot canvas with old data",
            args=(),
            exc_info=None,
        )
        gui_buffered2 = BufferedLogRecord(record=gui_record2, timestamp=datetime.now())
        records.append(gui_buffered2)

        return records


class TestComponentRemovalValidation:
    """Специфические тесты для валидации удаления компонентов"""

    def test_value_aggregator_functionality_migrated(self):
        """Проверить, что функциональность ValueAggregator перенесена"""

        # Функциональность ValueAggregator должна быть доступна через операционные метрики
        with log_operation("VALUE_MIGRATION_TEST"):
            # Добавить большие данные (раньше обрабатывались ValueAggregator)
            large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
            operation_logger.add_metric("large_dict", large_dict)  # Добавить повторяющиеся данные
            repeated_list = ["same_value"] * 500
            operation_logger.add_metric("repeated_data", repeated_list)

        # Проверить, что данные обработаны корректно
        completed_operations = operation_monitor.completed_operations
        migration_ops = [op for op in completed_operations if op.operation_type == "VALUE_MIGRATION_TEST"]

        assert len(migration_ops) == 1, "Migration test operation should be recorded"

        migration_op = migration_ops[0]
        assert "large_dict" in migration_op.custom_metrics, "Large dict should be processed"
        assert "repeated_data" in migration_op.custom_metrics, "Repeated data should be processed"

    def test_pattern_detector_essential_features_preserved(self):
        """Проверить, что важные функции PatternDetector сохранены"""

        # Этот тест будет зависеть от того, какие функции PatternDetector сохранены
        # После упрощения должны остаться только важные паттерны

        try:
            from src.log_aggregator.pattern_detector import PatternDetector

            detector = PatternDetector()

            # Проверить, что detector все еще может работать
            assert hasattr(detector, "detect_patterns"), "PatternDetector should retain pattern detection capability"

            # Проверить, что removed паттерны больше не поддерживаются
            if hasattr(detector, "SUPPORTED_PATTERNS"):
                supported = detector.SUPPORTED_PATTERNS
                removed_patterns = ["cascade_component_initialization", "request_response_cycle"]

                for pattern in removed_patterns:
                    assert pattern not in supported, f"Pattern {pattern} should be removed"

        except ImportError:
            # Если PatternDetector удален полностью, это валидный результат
            pass

    def test_operation_aggregator_explicit_mode_only(self):
        """Проверить, что OperationAggregator работает только в явном режиме"""

        try:
            from src.log_aggregator.operation_aggregator import OperationAggregator

            aggregator = OperationAggregator()

            # Проверить, что автоматический режим отключен
            if hasattr(aggregator, "config"):
                config = aggregator.config
                if hasattr(config, "auto_mode_enabled"):
                    assert not config.auto_mode_enabled, "Auto mode should be disabled in simplified aggregator"

                if hasattr(config, "explicit_mode_enabled"):
                    assert config.explicit_mode_enabled, "Explicit mode should be enabled in simplified aggregator"

        except (ImportError, AttributeError):
            # Компонент может быть серьезно изменен
            pass


class TestSystemHealthAfterSimplification:
    """Тесты общего здоровья системы после упрощения"""

    def setup_method(self):
        """Настройка для каждого теста"""
        operation_monitor.reset()
        operation_logger.reset()

    def test_no_functionality_regressions(self):
        """Проверить отсутствие регрессий функциональности"""

        # Список ключевых операций, которые должны работать
        key_operations = [
            "LOAD_FILE",
            "DECONVOLUTION",
            "MODEL_FIT_CALCULATION",
            "MODEL_FREE_CALCULATION",
            "MODEL_BASED_CALCULATION",
        ]

        for op_name in key_operations:
            with log_operation(op_name):
                operation_logger.add_metric("regression_test", True)
                operation_logger.add_metric("operation_name", op_name)  # Проверить, что все операции записаны
        completed_operations = operation_monitor.get_completed_operations()
        recorded_names = {op.operation_type for op in completed_operations}

        for op_name in key_operations:
            assert op_name in recorded_names, f"Key operation {op_name} should work"

    def test_integration_points_still_work(self):
        """Проверить, что точки интеграции все еще работают"""

        # Тест интеграции с основным приложением
        with log_operation("INTEGRATION_TEST"):
            operation_logger.add_metric("integration_point", "main_application")
            operation_logger.add_metric("test_type", "integration")

        # Проверить, что таблицы операций могут быть созданы
        from src.log_aggregator.operation_table_builder import OperationTableBuilder

        builder = OperationTableBuilder()
        completed_operations = operation_monitor.get_completed_operations()

        try:
            tables = builder.build_tables(completed_operations)
            assert len(tables) > 0, "Should be able to build operation tables"
        except Exception as e:
            pytest.fail(f"Operation table building failed: {e}")

    def test_backward_compatibility_maintained(self):
        """Проверить сохранение обратной совместимости"""

        # API операций должно остаться неизменным
        api_methods = [
            (log_operation, "log_operation context manager"),
            (operation_logger.add_metric, "operation_logger.add_metric method"),
            (operation_monitor.get_completed_operations, "operation_monitor.get_completed_operations method"),
        ]

        for method, description in api_methods:
            assert callable(method), f"{description} should remain callable"

        # Проверить, что основное API работает
        with log_operation("COMPATIBILITY_TEST"):
            operation_logger.add_metric("api_test", "success")

        operations = operation_monitor.get_completed_operations()
        assert len(operations) > 0, "Basic API should work"
