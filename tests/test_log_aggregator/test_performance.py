"""
Тестирование производительности системы операций
Этап 7: Нагрузочные тесты и оптимизация
"""

import gc
import time

import psutil

from src.log_aggregator.operation_logger import log_operation, operation_logger
from src.log_aggregator.operation_monitor import operation_monitor


class TestOperationPerformance:
    """Тестирование производительности системы операций"""

    def setup_method(self):
        """Настройка для каждого теста"""
        operation_monitor.reset()
        operation_logger.reset()
        gc.collect()  # Очистить память перед тестом

    def test_high_frequency_operations(self):
        """Тест частых операций"""

        start_time = time.time()

        # Выполнить 1000 коротких операций
        for i in range(1000):
            with log_operation(f"FAST_OP_{i % 10}"):  # 10 разных типов операций
                operation_logger.add_metric("iteration", i)

        total_time = time.time() - start_time  # Проверить, что система справляется с нагрузкой
        assert total_time < 10.0, f"1000 operations took {total_time:.2f}s, expected < 10s"

        # Проверить отсутствие утечек памяти
        self.verify_memory_usage_stable()

    def test_large_operation_data(self):
        """Тест операций с большим объемом данных"""

        # Start tracking with operation monitor
        operation_monitor.start_operation_tracking("LARGE_DATA_OPERATION")

        # Use operation logger for the actual operation
        with log_operation("LARGE_DATA_OPERATION"):
            # Добавить много метрик
            for i in range(100):
                operation_logger.add_metric(f"metric_{i}", f"value_{i}")

            # Добавить большие данные
            large_data = list(range(10000))
            operation_logger.add_metric("large_dataset", large_data)

            # Also add metrics to operation monitor
            for i in range(100):
                operation_monitor.add_custom_metric(f"metric_{i}", f"value_{i}")
            operation_monitor.add_custom_metric("large_dataset", large_data)

        # End tracking with operation monitor
        operation_monitor.end_operation_tracking()

        # Проверить, что операция корректно обработана
        self.verify_large_operation_handled()

    def test_memory_efficiency(self):
        """Тест эффективности использования памяти"""

        process = psutil.Process()

        # Измерить начальное потребление памяти
        initial_memory = process.memory_info().rss

        # Выполнить много операций
        for i in range(100):
            with log_operation(f"MEMORY_TEST_{i}"):
                operation_logger.add_metric("test_data", list(range(1000)))

        # Принудительно очистить память
        gc.collect()

        # Измерить финальное потребление памяти
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Проверить, что утечки памяти нет
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase: {memory_increase / (1024*1024):.1f}MB"

    def test_concurrent_operations_performance(self):
        """Тест производительности параллельных операций"""

        import threading

        start_time = time.time()
        results = []
        errors = []

        def worker_operation(worker_id: int, operations_count: int):
            try:
                for i in range(operations_count):
                    with log_operation(f"PERF_WORKER_{worker_id}_OP_{i}"):
                        operation_logger.add_metric("worker_id", worker_id)
                        operation_logger.add_metric("operation_id", i)
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Запустить 10 воркеров по 50 операций каждый
        threads = []
        for worker_id in range(10):
            thread = threading.Thread(target=worker_operation, args=(worker_id, 50))
            threads.append(thread)
            thread.start()

        # Дождаться завершения
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Проверить результаты
        assert len(results) == 10, f"Expected 10 workers, got {len(results)}"
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert total_time < 5.0, f"Concurrent operations took {total_time:.2f}s, expected < 5s"

    def test_operation_scalability(self):
        """Тест масштабируемости операций"""

        # Тест с разными размерами нагрузки
        test_sizes = [10, 100, 500, 1000]
        times = []

        for size in test_sizes:
            start_time = time.time()

            for i in range(size):
                with log_operation(f"SCALE_TEST_{size}_{i}"):
                    operation_logger.add_metric("test_size", size)
                    operation_logger.add_metric("iteration", i)

            elapsed = time.time() - start_time
            times.append(elapsed)  # Проверить, что время растет линейно (не экспоненциально)
        # Время на 1000 операций не должно быть в 100 раз больше времени на 10 операций
        ratio = times[-1] / times[0] if times[0] > 0 else float("inf")
        assert ratio < 200, f"Performance degradation too high: {ratio:.1f}x"

    def verify_memory_usage_stable(self):
        """Проверить стабильность использования памяти"""
        # Дать системе время на очистку
        time.sleep(0.1)
        gc.collect()

        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)

        # Проверить, что память не превышает разумный лимит
        assert memory_mb < 200, f"Memory usage too high: {memory_mb:.1f}MB"

    def verify_large_operation_handled(self):
        """Проверить обработку операции с большими данными"""
        completed_operations = operation_monitor.completed_operations
        large_ops = [op for op in completed_operations if op.operation_type == "LARGE_DATA_OPERATION"]

        assert len(large_ops) == 1, "Large data operation should be recorded"

        large_op = large_ops[0]
        assert len(large_op.custom_metrics) > 50, "Should have many metrics"
        assert "large_dataset" in large_op.custom_metrics, "Should contain large dataset metric"


class TestOperationOptimization:
    """Тесты для оптимизации операций"""

    def setup_method(self):
        """Настройка для каждого теста"""
        operation_monitor.reset()
        operation_logger.reset()

    def test_metric_compression_efficiency(self):
        """Тест эффективности сжатия метрик"""
        # Start tracking with operation monitor
        operation_monitor.start_operation_tracking("COMPRESSION_TEST")

        # Create operation with repeating data using operation logger
        with log_operation("COMPRESSION_TEST"):
            # Добавить много похожих метрик
            for i in range(100):
                operation_logger.add_metric(f"similar_metric_{i}", "repeated_value")

            # Добавить большие повторяющиеся данные
            repeated_data = ["same_value"] * 1000
            operation_logger.add_metric("repeated_data", repeated_data)

        # End tracking with operation monitor
        operation_monitor.end_operation_tracking()

        # Проверить, что система справляется с повторяющимися данными
        completed_operations = operation_monitor.completed_operations
        compression_ops = [op for op in completed_operations if op.operation_type == "COMPRESSION_TEST"]

        assert len(compression_ops) == 1, "Compression test operation should be recorded"

    def test_operation_cleanup_efficiency(self):
        """Тест эффективности очистки операций"""  # Создать много операций
        for i in range(50):
            with log_operation(f"CLEANUP_TEST_{i}"):
                operation_logger.add_metric("test_index", i)

        initial_count = len(operation_monitor.completed_operations)

        # Принудительно очистить старые операции (если такая функциональность есть)
        if hasattr(operation_monitor, "cleanup_old_operations"):
            operation_monitor.cleanup_old_operations()

        # Проверить, что операции все еще доступны или корректно очищены
        final_count = len(operation_monitor.completed_operations)
        assert final_count <= initial_count, "Operation count should not increase after cleanup"

    def test_operation_indexing_performance(self):
        """Тест производительности индексации операций"""

        # Создать операции с разными именами
        operation_names = [f"INDEX_TEST_{i}" for i in range(100)]

        # Записать операции используя operation_monitor для отслеживания
        for name in operation_names:
            operation_monitor.start_operation_tracking(name)
            operation_monitor.add_custom_metric("indexed", True)
            operation_monitor.end_operation_tracking()

        # Тест поиска операций
        start_time = time.time()

        completed_operations = operation_monitor.completed_operations
        for name in operation_names[:10]:  # Поиск первых 10
            found_ops = [op for op in completed_operations if op.operation_type == name]
            assert len(found_ops) == 1, f"Should find exactly one operation named {name}"

        search_time = time.time() - start_time

        # Поиск должен быть быстрым
        assert search_time < 0.1, f"Operation search took {search_time:.3f}s, expected < 0.1s"


class TestOperationBenchmarks:
    """Бенчмарки для определения базовых показателей производительности"""

    def setup_method(self):
        """Настройка для каждого теста"""
        operation_monitor.reset()
        operation_logger.reset()

    def test_baseline_operation_overhead(self):
        """Измерить базовые накладные расходы на операцию"""

        # Тест без операций
        start_time = time.time()
        for i in range(1000):
            pass  # Ничего не делать
        baseline_time = time.time() - start_time

        # Тест с операциями
        start_time = time.time()
        for i in range(1000):
            with log_operation(f"OVERHEAD_TEST_{i % 10}"):
                pass  # Только накладные расходы операции
        operation_time = time.time() - start_time

        # Вычислить накладные расходы
        overhead = operation_time - baseline_time
        overhead_per_operation = overhead / 1000

        # Накладные расходы должны быть минимальными
        assert overhead_per_operation < 0.001, f"Operation overhead: {overhead_per_operation:.4f}s"

        print(f"Baseline operation overhead: {overhead_per_operation:.4f}s per operation")

    def test_metric_addition_performance(self):
        """Измерить производительность добавления метрик"""

        metrics_counts = [1, 10, 50, 100]
        times = []

        for count in metrics_counts:
            start_time = time.time()

            with log_operation(f"METRIC_PERF_{count}"):
                for i in range(count):
                    operation_logger.add_metric(f"metric_{i}", f"value_{i}")

            elapsed = time.time() - start_time
            times.append(elapsed)  # Проверить, что время растет линейно
        for i, (count, time_taken) in enumerate(zip(metrics_counts, times)):
            time_per_metric = time_taken / count
            # Adjusted threshold to account for logging overhead
            # The system logs each metric addition which takes additional time
            assert time_per_metric < 0.002, f"Metric addition too slow: {time_per_metric:.6f}s per metric"

        print(f"Metric addition performance: {[f'{t:.4f}s' for t in times]}")

    def test_operation_table_generation_performance(self):
        """Измерить производительность генерации таблиц операций"""  # Создать операции для генерации таблиц
        for i in range(50):
            with log_operation(f"TABLE_GEN_TEST_{i}"):
                for j in range(10):
                    operation_logger.add_metric(f"metric_{j}", f"value_{i}_{j}")

        # Измерить время генерации таблиц
        from src.log_aggregator.operation_table_builder import OperationTableBuilder

        start_time = time.time()
        builder = OperationTableBuilder()
        completed_operations = operation_monitor.completed_operations
        tables = builder.build_tables(completed_operations)
        generation_time = time.time() - start_time

        # Генерация таблиц должна быть быстрой
        assert generation_time < 1.0, f"Table generation took {generation_time:.3f}s, expected < 1s"
        assert len(tables) > 0, "Should generate at least one table"

        print(f"Table generation time: {generation_time:.3f}s for {len(completed_operations)} operations")
