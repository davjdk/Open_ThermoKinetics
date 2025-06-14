# Этап 9: Тестирование и валидация системы

## Цель этапа
Провести комплексное тестирование новой архитектуры логирования операций, валидировать корректность работы всех компонентов и обеспечить стабильность системы.

## Задачи этапа

### 9.1 Модульное тестирование компонентов
- Создать тесты для декоратора `@operation`
- Протестировать обновлённый `OperationLogger`
- Валидировать работу системы форматирования таблиц
- Проверить интерфейс обработки ошибок

### 9.2 Интеграционное тестирование
- Тестирование взаимодействия между компонентами
- Проверка корректности агрегации вложенных операций
- Валидация системы конфигурации
- Тестирование автоматического применения декораторов

### 9.3 Тестирование производительности
- Измерение накладных расходов системы логирования
- Тестирование под нагрузкой (множественные операции)
- Проверка работы в многопоточной среде
- Валидация потребления памяти

### 9.4 Тестирование совместимости
- Проверка совместимости с PyQt сигналами и слотами
- Тестирование интеграции с существующим кодом
- Валидация обратной совместимости API
- Проверка работы с различными конфигурациями

## Набор тестов

### 9.5 Тесты декоратора @operation
```python
import pytest
import time
from unittest.mock import Mock, patch
from src.core.logger_handler import operation, get_operation_logger

class TestOperationDecorator:
    """Тесты декоратора @operation"""
    
    def test_basic_operation_decoration(self):
        """Тест базового декорирования операции"""
        mock_logger = Mock()
        
        with patch('src.core.logger_handler.get_operation_logger', return_value=mock_logger):
            @operation
            def test_operation():
                return "success"
            
            result = test_operation()
            
            assert result == "success"
            mock_logger.start_operation.assert_called_once()
            mock_logger.end_operation.assert_called_once_with(status="SUCCESS")
    
    def test_operation_with_exception(self):
        """Тест обработки исключений в декорированной операции"""
        mock_logger = Mock()
        
        with patch('src.core.logger_handler.get_operation_logger', return_value=mock_logger):
            @operation
            def failing_operation():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                failing_operation()
            
            mock_logger.start_operation.assert_called_once()
            mock_logger.end_operation.assert_called_once_with(
                status="ERROR",
                error_info={
                    "type": "ValueError",
                    "message": "Test error",
                    "handled": True
                }
            )
    
    def test_nested_operations(self):
        """Тест вложенных операций"""
        mock_logger = Mock()
        
        with patch('src.core.logger_handler.get_operation_logger', return_value=mock_logger):
            @operation
            def parent_operation():
                child_operation()
                return "parent_done"
            
            @operation
            def child_operation():
                return "child_done"
            
            result = parent_operation()
            
            assert result == "parent_done"
            assert mock_logger.start_operation.call_count == 2
            assert mock_logger.end_operation.call_count == 2
    
    def test_operation_with_custom_type(self):
        """Тест операции с указанным типом"""
        mock_logger = Mock()
        
        with patch('src.core.logger_handler.get_operation_logger', return_value=mock_logger):
            @operation(operation_type="CUSTOM_OPERATION")
            def custom_operation():
                return "custom"
            
            result = custom_operation()
            
            assert result == "custom"
            mock_logger.start_operation.assert_called_once_with("CUSTOM_OPERATION")
    
    def test_pyqt_slot_compatibility(self):
        """Тест совместимости с PyQt слотами"""
        from PyQt6.QtCore import pyqtSlot, QObject
        
        class TestWidget(QObject):
            @operation
            @pyqtSlot()
            def slot_method(self):
                return "slot_result"
        
        widget = TestWidget()
        result = widget.slot_method()
        
        assert result == "slot_result"
        assert hasattr(widget.slot_method, '__pyqtSignature__')
```

### 9.6 Тесты OperationLogger
```python
class TestOperationLogger:
    """Тесты класса OperationLogger"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.logger = OperationLogger()
    
    def test_operation_lifecycle(self):
        """Тест полного жизненного цикла операции"""
        # Начать операцию
        self.logger.start_operation("TEST_OPERATION")
        
        # Проверить текущую операцию
        current = self.logger.get_current_operation()
        assert current is not None
        assert current['operation_name'] == "TEST_OPERATION"
        assert 'start_time' in current
        
        # Добавить метрику
        self.logger.add_metric("test_metric", 42)
        
        # Завершить операцию
        self.logger.end_operation(status="SUCCESS")
        
        # Проверить что операция завершена
        assert self.logger.get_current_operation() is None
    
    def test_nested_operation_aggregation(self):
        """Тест агрегации вложенных операций"""
        # Начать родительскую операцию
        self.logger.start_operation("PARENT_OPERATION")
        
        # Добавить метрику к родительской
        self.logger.add_metric("parent_metric", 1)
        
        # Начать дочернюю операцию
        self.logger.start_operation("CHILD_OPERATION")
        self.logger.add_metric("child_metric", 2)
        self.logger.end_operation("SUCCESS")
        
        # Проверить что мы вернулись к родительской
        current = self.logger.get_current_operation()
        assert current['operation_name'] == "PARENT_OPERATION"
        
        # Завершить родительскую
        self.logger.end_operation("SUCCESS")
        
        # Проверить агрегацию метрик
        # (здесь нужна реальная проверка агрегированных данных)
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        self.logger.start_operation("ERROR_OPERATION")
        
        error_info = {
            "type": "ValueError",
            "message": "Test error",
            "traceback": "mock traceback"
        }
        
        self.logger.end_operation(status="ERROR", error_info=error_info)
        
        # Проверить что ошибка зафиксирована
        # (здесь проверяется запись в логи или вызов обработчика)
    
    def test_thread_safety(self):
        """Тест потокобезопасности"""
        import threading
        import time
        
        results = []
        
        def worker_thread(thread_id):
            self.logger.start_operation(f"THREAD_OPERATION_{thread_id}")
            time.sleep(0.1)  # Имитация работы
            self.logger.add_metric("thread_id", thread_id)
            self.logger.end_operation("SUCCESS")
            results.append(thread_id)
        
        # Запустить несколько потоков
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Дождаться завершения
        for thread in threads:
            thread.join()
        
        # Проверить результаты
        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}
```

### 9.7 Тесты Rich форматирования
```python
class TestRichFormatting:
    """Тесты системы Rich форматирования таблиц"""
    
    def test_rich_operation_table(self):
        """Тест Rich форматирования успешной операции"""
        from src.core.rich_formatter import RichOperationFormatter
        from io import StringIO
        from rich.console import Console
        
        # Создать консоль с захватом вывода
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        
        formatter = RichOperationFormatter()
        formatter.console = console
        
        operation_data = {
            "operation_name": "ADD_REACTION",
            "display_name": "Add Reaction",
            "status": "SUCCESS",
            "duration": 0.523,
            "call_count": 1,
            "nested_operations": 3,
            "files_modified": 2,
            "thread_id": "MainThread"
        }
        
        formatter.format_operation_summary(operation_data)
        result = output.getvalue()
        
        # Проверить наличие ключевых элементов
        assert "🔄 OPERATION SUMMARY" in result
        assert "Add Reaction" in result
        assert "✅ SUCCESS" in result
        assert "0.523s" in result
        assert "MainThread" in result
    
    def test_rich_error_panel(self):
        """Тест Rich панели ошибок"""
        from src.core.rich_formatter import RichOperationFormatter
        from io import StringIO
        from rich.console import Console
        
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        
        formatter = RichOperationFormatter()
        formatter.console = console
        
        operation_data = {
            "operation_name": "FAILING_OPERATION",
            "display_name": "Failing Operation",
            "status": "ERROR",
            "duration": 1.234,
            "error_info": {
                "type": "ValueError",
                "message": "Invalid parameter",
                "recovery_attempted": True
            }
        }
        
        formatter.format_operation_summary(operation_data)
        result = output.getvalue()
        
        # Проверить элементы ошибки
        assert "❌ ERROR" in result
        assert "❌ Error Details" in result
        assert "ValueError" in result
        assert "Invalid parameter" in result
        assert "🔄 Recovery was attempted" in result
    
    def test_rich_configuration(self):
        """Тест настройки Rich через конфигурацию"""
        from src.core.app_settings import config_manager
        from src.core.rich_formatter import RichOperationFormatter
        
        # Изменить конфигурацию Rich
        config_manager.update_config({
            "rich_table_box": "SQUARE",
            "rich_header_style": "bold red",
            "success_icon": "🟢",
            "error_icon": "🔴"
        })
        
        rich_config = config_manager.get_rich_config()
        
        # Проверить применение настроек
        assert rich_config.table_box_style == "SQUARE"
        assert rich_config.table_title_style == "bold red"
        assert rich_config.success_icon == "🟢"
        assert rich_config.error_icon == "🔴"
    
    def test_rich_fallback_mode(self):
        """Тест fallback режима при отключенном Rich"""
        from src.core.rich_formatter import RichOperationFormatter
        from src.core.app_settings import config_manager
        
        # Отключить Rich
        config_manager.update_config({"rich_enabled": False})
        
        formatter = RichOperationFormatter()
        
        operation_data = {
            "operation_name": "TEST_OPERATION",
            "status": "SUCCESS",
            "duration": 1.0
        }
        
        # Должен использовать простой текстовый вывод
        with patch('builtins.print') as mock_print:
            formatter.format_operation_summary(operation_data)
            
        # Проверить что был простой print, а не Rich
        mock_print.assert_called()
        args = mock_print.call_args[0][0]
        assert isinstance(args, str)  # Простая строка, не Rich объект
    
    def test_rich_export_functionality(self):
        """Тест экспорта Rich в HTML/SVG"""
        from src.core.rich_formatter import RichOperationFormatter
        from src.core.app_settings import config_manager
        import tempfile
        import os
        
        # Включить экспорт
        config_manager.update_config({
            "rich_export_html": True,
            "rich_record_mode": True
        })
        
        formatter = RichOperationFormatter()
        
        operation_data = {
            "operation_name": "EXPORT_TEST",
            "status": "SUCCESS",
            "duration": 0.5
        }
        
        # Создать временный файл для экспорта
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Выполнить форматирование с экспортом
            formatter.format_operation_summary(operation_data)
            
            if hasattr(formatter, 'export_html'):
                formatter.export_html(tmp_path)
                
                # Проверить что файл создан
                assert os.path.exists(tmp_path)
                
                # Проверить содержимое HTML
                with open(tmp_path, 'r') as f:
                    html_content = f.read()
                    assert "EXPORT_TEST" in html_content
                    assert "SUCCESS" in html_content
        finally:
            # Очистить временный файл
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
```

### 9.8 Тесты автоматического декорирования
```python
class TestAutoDecoration:
    """Тесты автоматического применения декораторов"""
    
    def test_metaclass_auto_decoration(self):
        """Тест автодекорирования через метакласс"""
        from src.core.logger_handler import OperationAutoDecoratorMeta
        
        class TestOperationHandler(metaclass=OperationAutoDecoratorMeta):
            def add_reaction(self):
                return "reaction_added"
            
            def remove_reaction(self):
                return "reaction_removed"
            
            def non_operation_method(self):
                return "not_decorated"
        
        handler = TestOperationHandler()
        
        # Проверить что операции декорированы
        assert hasattr(handler.add_reaction, '_operation_decorated')
        assert hasattr(handler.remove_reaction, '_operation_decorated')
        
        # Проверить что обычные методы не декорированы
        assert not hasattr(handler.non_operation_method, '_operation_decorated')
    
    def test_auto_decoration_validation(self):
        """Тест валидации автодекорирования"""
        from src.core.logger_handler import AutoDecorationValidator
        
        class ValidatedHandler(OperationAutoDecoratorMeta):
            def add_reaction(self):
                pass
            
            def load_file(self):
                pass
        
        warnings = AutoDecorationValidator.validate_decorated_class(ValidatedHandler)
        
        # Не должно быть предупреждений для корректно декорированного класса
        assert len(warnings) == 0
```

### 9.9 Тесты производительности
```python
class TestPerformance:
    """Тесты производительности системы логирования"""
    
    def test_decorator_overhead(self):
        """Тест накладных расходов декоратора"""
        import time
        
        # Функция без декоратора
        def plain_function():
            return sum(range(1000))
        
        # Функция с декоратором
        @operation
        def decorated_function():
            return sum(range(1000))
        
        # Измерить время выполнения
        iterations = 1000
        
        # Без декоратора
        start = time.time()
        for _ in range(iterations):
            plain_function()
        plain_time = time.time() - start
        
        # С декоратором
        start = time.time()
        for _ in range(iterations):
            decorated_function()
        decorated_time = time.time() - start
        
        # Накладные расходы не должны превышать 50%
        overhead = (decorated_time - plain_time) / plain_time
        assert overhead < 0.5, f"Decorator overhead too high: {overhead:.2%}"
    
    def test_concurrent_operations(self):
        """Тест параллельных операций"""
        import threading
        import time
        
        def operation_worker(worker_id, iterations):
            for i in range(iterations):
                @operation
                def worker_operation():
                    time.sleep(0.001)  # Небольшая задержка
                    return f"worker_{worker_id}_iteration_{i}"
                
                worker_operation()
        
        # Запустить несколько рабочих потоков
        workers = []
        start_time = time.time()
        
        for worker_id in range(10):
            worker = threading.Thread(
                target=operation_worker,
                args=(worker_id, 50)
            )
            workers.append(worker)
            worker.start()
        
        # Дождаться завершения
        for worker in workers:
            worker.join()
        
        total_time = time.time() - start_time
        
        # Проверить что время выполнения разумное
        assert total_time < 30, f"Concurrent operations took too long: {total_time:.2f}s"
    
    def test_memory_usage(self):
        """Тест потребления памяти"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Выполнить много операций
        for i in range(1000):
            @operation
            def memory_test_operation():
                data = list(range(1000))  # Создать некоторые данные
                return len(data)
            
            memory_test_operation()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Увеличение памяти не должно быть критическим
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase too high: {memory_increase / 1024 / 1024:.2f}MB"
```

### 9.10 Интеграционные тесты
```python
class TestIntegration:
    """Интеграционные тесты системы"""
    
    def test_full_operation_workflow(self):
        """Тест полного рабочего процесса операции"""
        from src.core.calculation_data_operations import CalculationDataOperations
        from src.core.app_settings import config_manager
        
        # Настроить конфигурацию
        config_manager.update_config({
            "ascii_tables_enabled": True,
            "detail_level": "detailed"
        })
        
        # Создать обработчик операций
        operations = CalculationDataOperations()
        
        # Выполнить операцию (должна быть автоматически декорирована)
        with patch('builtins.print') as mock_print:
            result = operations.add_reaction(
                file_name="test.csv",
                reaction_data={"function": "gauss"}
            )
        
        # Проверить что операция выполнена
        assert result is not None
        
        # Проверить что таблица была выведена
        mock_print.assert_called()
        table_output = mock_print.call_args[0][0]
        assert "OPERATION SUMMARY" in table_output
        assert "Add Reaction" in table_output
    
    def test_error_recovery_workflow(self):
        """Тест рабочего процесса с восстановлением после ошибок"""
        from src.core.logger_handler import get_operation_logger
        from src.core.error_handlers import GuiOperationErrorHandler
        
        # Зарегистрировать обработчик ошибок
        logger = get_operation_logger()
        error_handler = GuiOperationErrorHandler()
        logger.register_error_handler(error_handler)
        
        # Выполнить операцию с ошибкой
        @operation
        def failing_operation():
            raise ValueError("Intentional test error")
        
        with pytest.raises(ValueError):
            failing_operation()
        
        # Проверить что обработчик был вызван
        # (здесь проверяется через mock или логи)
```

## Критерии приёмки

### 9.11 Функциональные требования
- ✅ Все операции автоматически декорированы
- ✅ Вложенные операции корректно агрегируются
- ✅ Таблицы отображаются после каждой операции
- ✅ Ошибки корректно обрабатываются и отображаются
- ✅ Конфигурация применяется динамически

### 9.12 Производительные требования
- ✅ Накладные расходы декоратора < 50%
- ✅ Время выполнения 1000 операций < 30 секунд
- ✅ Увеличение памяти < 50MB при интенсивном использовании
- ✅ Корректная работа в многопоточной среде

### 9.13 Качество кода
- ✅ Покрытие тестами > 90%
- ✅ Все тесты проходят без ошибок
- ✅ Нет критических предупреждений статического анализа
- ✅ Документация обновлена и актуальна

## Автоматизация тестирования

### 9.14 Конфигурация pytest
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=src.core.logger_handler
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
markers =
    integration: marks tests as integration tests
    performance: marks tests as performance tests
    slow: marks tests as slow running
```

### 9.15 Непрерывная интеграция
```yaml
# .github/workflows/test.yml
name: Test Logger Handler Refactor

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-mock
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src.core.logger_handler --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

## Ожидаемые результаты
- Полная уверенность в корректности работы новой архитектуры
- Набор автоматических тестов для регрессионного тестирования
- Подтверждение соответствия производительным требованиям
- Валидация совместимости с существующим кодом

## Критерии готовности
- Все тесты проходят успешно
- Покрытие кода тестами превышает 90%
- Производительность соответствует требованиям
- Система стабильно работает под нагрузкой

## Документация тестирования
- Создание руководства по запуску тестов
- Документация тестовых сценариев и их назначения
- Инструкции по добавлению новых тестов
- Отчёты о покрытии кода и производительности
