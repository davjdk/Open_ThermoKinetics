# Этап 4: Комплексное тестирование и валидация исправлений

## Цель этапа
Провести всестороннее тестирование внесенных исправлений, создать автоматизированные тесты для предотвращения регрессий и валидировать стабильность системы логирования.

## Охват тестирования

### 1. Модульные тесты компонентов агрегатора
**Новые тестовые файлы**:
- `tests/test_log_aggregator/test_safe_message_handling.py`
- `tests/test_log_aggregator/test_recursion_prevention.py`
- `tests/test_log_aggregator/test_value_aggregator_safety.py`
- `tests/test_log_aggregator/test_pattern_detector_safety.py`
- `tests/test_log_aggregator/test_error_expansion_safety.py`

### 2. Тестирование безопасного получения сообщений

**Файл**: `tests/test_log_aggregator/test_safe_message_handling.py`

```python
import logging
import pytest
from unittest.mock import MagicMock, patch

from src.log_aggregator.safe_message_utils import safe_get_message, safe_extract_args
from src.log_aggregator.value_aggregator import ValueAggregator
from src.log_aggregator.pattern_detector import PatternDetector
from src.log_aggregator.error_expansion import ErrorExpansionEngine


class TestSafeMessageHandling:
    """Test safe message handling across aggregator components."""
    
    def test_safe_get_message_with_format_errors(self):
        """Test safe_get_message with various formatting errors."""
        test_cases = [
            # (msg, args, expected_substring)
            ("Test error %d %s", (42,), "Test error"),  # Missing arg
            ("Value: %d", ("text",), "Value:"),          # Wrong type
            ("Format %s", (1, 2), "Format"),             # Extra arg
            ("No format", (), "No format"),              # No format
            ("%s %d %f", (), "%s %d %f"),               # No args with format
        ]
        
        for msg, args, expected in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0,
                msg=msg, args=args, exc_info=None
            )
            
            result = safe_get_message(record)
            assert expected in result
            assert isinstance(result, str)
    
    def test_value_aggregator_with_bad_formatting(self):
        """Test ValueAggregator handles formatting errors gracefully."""
        from src.log_aggregator.buffer_manager import BufferedLogRecord
        from datetime import datetime
        
        aggregator = ValueAggregator()
        
        # Create problematic log record
        bad_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Array data: %s with size %d", args=(None,), exc_info=None
        )
        
        buffered = BufferedLogRecord(record=bad_record, timestamp=datetime.now())
        
        # Should not raise exception
        result = aggregator.process_message(buffered)
        assert isinstance(result, str)
    
    def test_pattern_detector_with_bad_formatting(self):
        """Test PatternDetector handles formatting errors gracefully."""
        from src.log_aggregator.buffer_manager import BufferedLogRecord
        from datetime import datetime
        
        detector = PatternDetector()
        
        # Create records with formatting issues
        records = []
        for i, (msg, args) in enumerate([
            ("Pattern %d %s", (i,)),        # Missing arg
            ("Another %s", (1, 2)),         # Extra arg
            ("Normal message", ()),         # Normal
        ]):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=msg, args=args, exc_info=None
            )
            buffered = BufferedLogRecord(record=record, timestamp=datetime.now())
            records.append(buffered)
        
        # Should not raise exception
        patterns = detector.detect_patterns(records)
        assert isinstance(patterns, list)
    
    def test_error_expansion_with_bad_formatting(self):
        """Test ErrorExpansionEngine handles formatting errors gracefully."""
        from src.log_aggregator.buffer_manager import BufferedLogRecord
        from datetime import datetime
        
        engine = ErrorExpansionEngine()
        
        # Create error record with formatting issue
        error_record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Error occurred: %s in module %s", args=("something",), exc_info=None
        )
        buffered_error = BufferedLogRecord(record=error_record, timestamp=datetime.now())
        
        # Should not raise exception
        result = engine.expand_error(buffered_error, [])
        assert result is not None
```

### 3. Тестирование предотвращения рекурсии

**Файл**: `tests/test_log_aggregator/test_recursion_prevention.py`

```python
import logging
import time
from unittest.mock import MagicMock, patch

from src.log_aggregator.realtime_handler import AggregatingHandler
from src.log_aggregator.config import AggregationConfig


class TestRecursionPrevention:
    """Test prevention of recursive log processing."""
    
    def test_internal_logger_filtering(self):
        """Test that internal log_aggregator messages are filtered out."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)
        
        # Internal aggregator message - should be forwarded directly
        internal_record = logging.LogRecord(
            name="log_aggregator.realtime_handler", level=logging.ERROR,
            pathname="", lineno=0, msg="Internal error", args=(), exc_info=None
        )
        
        handler.emit(internal_record)
        
        # Should be forwarded directly without aggregation
        target_handler.emit.assert_called_once_with(internal_record)
        
        # External message - should go through aggregation
        target_handler.reset_mock()
        external_record = logging.LogRecord(
            name="app.module", level=logging.INFO,
            pathname="", lineno=0, msg="App message", args=(), exc_info=None
        )
        
        handler.emit(external_record)
        
        # Should be processed (buffered, not immediately forwarded)
        # Since it goes to buffer, target_handler.emit should not be called immediately
        assert target_handler.emit.call_count == 0
    
    def test_cascade_error_prevention(self):
        """Test prevention of cascading internal errors."""
        target_handler = MagicMock()
        config = AggregationConfig()
        
        # Mock internal error in value aggregator
        with patch('src.log_aggregator.realtime_handler.AggregatingHandler._handle_internal_error') as mock_error_handler:
            handler = AggregatingHandler(target_handler, config)
            
            # Force internal error by mocking value_aggregator
            handler.value_aggregator.process_message = MagicMock(side_effect=Exception("Formatting error"))
            
            # This should trigger internal error handling
            test_record = logging.LogRecord(
                name="app.test", level=logging.INFO,
                pathname="", lineno=0, msg="Test message", args=(), exc_info=None
            )
            
            handler.emit(test_record)
            
            # Internal error should be caught and handled
            mock_error_handler.assert_called()
    
    def test_error_threshold_degradation(self):
        """Test automatic degradation when error threshold is exceeded."""
        target_handler = MagicMock()
        config = AggregationConfig()
        handler = AggregatingHandler(target_handler, config)
        
        # Set low threshold for testing
        handler._max_internal_errors = 3
        
        # Simulate multiple internal errors
        for i in range(5):
            handler._handle_internal_error(Exception(f"Error {i}"))
        
        # After threshold, features should be disabled
        assert not handler.enable_error_expansion
        assert not handler.enable_value_aggregation
```

### 4. Интеграционные тесты

**Файл**: `tests/test_log_aggregator/test_integration_stability.py`

```python
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from src.core.logger_config import LoggerManager


class TestIntegrationStability:
    """Integration tests for overall system stability."""
    
    def test_high_volume_logging(self):
        """Test system stability under high volume logging."""
        # Configure minimal aggregation for performance
        LoggerManager.configure_logging(
            enable_aggregation=True,
            aggregation_preset="minimal"
        )
        
        logger = LoggerManager.get_logger("stress_test")
        
        def log_worker(worker_id: int, num_messages: int):
            """Worker function for concurrent logging."""
            for i in range(num_messages):
                # Mix of normal and problematic messages
                if i % 10 == 0:
                    # Problematic formatting
                    logger.error("Worker %d error %s", worker_id)  # Missing arg
                else:
                    logger.info(f"Worker {worker_id} message {i}")
        
        # Run concurrent logging
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(log_worker, worker_id, 100)
                for worker_id in range(5)
            ]
            
            # Wait for completion
            for future in futures:
                future.result(timeout=30)
        
        # System should still be responsive
        test_logger = LoggerManager.get_logger("post_stress")
        test_logger.info("System responsive after stress test")
        
        # Get health status
        health = LoggerManager.get_logger_health_status()
        assert health["status"] in ["healthy", "degraded"]  # Not "unhealthy"
    
    def test_mixed_error_scenarios(self):
        """Test system with mixed error scenarios."""
        LoggerManager.configure_logging(
            enable_aggregation=True,
            aggregation_preset="development"
        )
        
        logger = LoggerManager.get_logger("mixed_test")
        
        # Various problematic scenarios
        error_scenarios = [
            ("Format error: %d %s", (42,)),           # Missing arg
            ("Type error: %d", ("string",)),          # Wrong type
            ("Extra args: %s", (1, 2, 3)),           # Extra args
            ("Unicode: %s", ("тест",)),               # Unicode
            ("None value: %s", (None,)),              # None
            ("Large data: %s", ([1] * 1000,)),       # Large data
        ]
        
        for msg, args in error_scenarios:
            try:
                logger.error(msg, *args)
            except Exception as e:
                pytest.fail(f"Logger should handle all scenarios gracefully: {e}")
        
        # Normal logging should still work
        logger.info("Normal message after error scenarios")
        
        # Check aggregator statistics
        stats = LoggerManager.get_aggregation_stats()
        assert stats["total_stats"]["total_records"] > 0
```

### 5. Производительность и утечки памяти

**Файл**: `tests/test_log_aggregator/test_performance_memory.py`

```python
import gc
import psutil
import time
from memory_profiler import profile

from src.core.logger_config import LoggerManager


class TestPerformanceMemory:
    """Test performance characteristics and memory usage."""
    
    def test_memory_stability_long_running(self):
        """Test memory stability during long-running operation."""
        LoggerManager.configure_logging(
            enable_aggregation=True,
            aggregation_preset="production"
        )
        
        logger = LoggerManager.get_logger("memory_test")
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run logging for extended period
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < 10:  # 10 seconds
            logger.info(f"Test message {message_count}")
            if message_count % 100 == 0:
                logger.error("Periodic error %d", message_count)
            message_count += 1
            
            if message_count % 1000 == 0:
                time.sleep(0.01)  # Small pause
        
        # Force garbage collection
        gc.collect()
        time.sleep(1)  # Allow cleanup
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (< 50MB for this test)
        assert memory_growth < 50 * 1024 * 1024, f"Memory growth too large: {memory_growth / 1024 / 1024:.1f} MB"
        
        print(f"Processed {message_count} messages")
        print(f"Memory growth: {memory_growth / 1024 / 1024:.1f} MB")
    
    def test_aggregator_cache_limits(self):
        """Test that aggregator caches respect size limits."""
        LoggerManager.configure_logging(
            enable_aggregation=True,
            aggregation_preset="development"
        )
        
        logger = LoggerManager.get_logger("cache_test")
        
        # Generate many different large values to stress the cache
        for i in range(200):  # More than typical cache limit
            large_data = list(range(1000))  # Large data structure
            logger.info("Processing data: %s", large_data)
        
        # Get aggregator statistics
        stats = LoggerManager.get_aggregation_stats()
        
        # Cache should be within limits
        # This assumes we can access cache statistics
        # Implementation may vary based on actual statistics structure
        assert stats["total_stats"]["total_records"] > 0
```

## Критерии прохождения тестов

### Функциональные критерии
- ✅ Все компоненты агрегатора обрабатывают некорректные сообщения без исключений
- ✅ Внутренние логи агрегатора не создают рекурсивные циклы
- ✅ Система автоматически деградирует при превышении порога ошибок
- ✅ Агрегированные логи остаются читаемыми и информативными

### Производительные критерии
- ✅ Обработка 100+ сообщений/сек без значительной деградации
- ✅ Стабильное потребление памяти при длительной работе
- ✅ Время обработки одного сообщения < 10ms (в среднем)
- ✅ Рост памяти < 1MB/час при нормальной нагрузке

### Надежность
- ✅ Отсутствие необработанных исключений в агрегаторе
- ✅ Корректное восстановление после внутренних ошибок
- ✅ Сохранение функциональности основного приложения при сбоях логгера

## Автоматизация тестирования

### CI/CD интеграция
```yaml
# .github/workflows/test_logger_stability.yml
name: Logger Stability Tests

on: [push, pull_request]

jobs:
  test_logger_stability:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install pytest memory-profiler psutil
    
    - name: Run logger stability tests
      run: |
        pytest tests/test_log_aggregator/ -v --tb=short
    
    - name: Run memory leak detection
      run: |
        pytest tests/test_log_aggregator/test_performance_memory.py -v -s
```

### Регрессионные тесты
**Создание базовых сценариев** для предотвращения возврата ошибок:
- Коллекция "проблемных" сообщений логов
- Автоматическая проверка при каждом коммите
- Benchmark производительности

## Результат этапа
По завершении этапа 4:
- Полное покрытие тестами всех исправлений
- Автоматизированное тестирование стабильности
- Валидация производительности и утечек памяти
- Регрессионные тесты для предотвращения повторных ошибок
- CI/CD интеграция для контроля качества

## Pull Request
**Название**: `test: Comprehensive testing suite for log aggregator stability`

**Описание**:
- Добавляет полный набор модульных тестов для безопасной обработки сообщений
- Создает интеграционные тесты для предотвращения рекурсии
- Включает нагрузочные тесты и тесты памяти
- Добавляет CI/CD пайплайн для автоматического тестирования
- Создает регрессионные тесты для предотвращения повторных ошибок

**Файлы для добавления**:
- `tests/test_log_aggregator/test_safe_message_handling.py`
- `tests/test_log_aggregator/test_recursion_prevention.py`
- `tests/test_log_aggregator/test_integration_stability.py`
- `tests/test_log_aggregator/test_performance_memory.py`
- `.github/workflows/test_logger_stability.yml`

**Зависимости для добавления**:
- `pytest`
- `memory-profiler`
- `psutil`
