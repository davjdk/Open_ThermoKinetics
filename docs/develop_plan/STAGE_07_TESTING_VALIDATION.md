# Этап 7: Комплексное тестирование и валидация BaseSignalsBurstStrategy

## Архитектура тестирования

### Многоуровневая стратегия тестирования

**Уровни тестирования**:
1. **Unit тесты**: отдельные методы BaseSignalsBurstStrategy
2. **Integration тесты**: взаимодействие с MetaOperationDetector  
3. **Performance тесты**: временные характеристики и нагрузочное тестирование
4. **E2E тесты**: полный цикл от операций до форматированного вывода
5. **Regression тесты**: сохранение существующей функциональности

### Тестовая среда

```python
# tests/test_base_signals_burst_strategy.py

import pytest
import time
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List

from src.core.log_aggregator.detection_strategies import BaseSignalsBurstStrategy
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.operation_log import OperationLog
from src.core.log_aggregator.meta_operation import MetaOperation


@dataclass
class MockCallerInfo:
    filename: str
    line_number: int
    function_name: str


class TestBaseSignalsBurstStrategy:
    """Комплексное тестирование BaseSignalsBurstStrategy."""
    
    @pytest.fixture
    def strategy_config(self):
        """Базовая конфигурация для тестов."""
        return {
            "time_window_ms": 100.0,
            "min_burst_size": 2,
            "max_gap_ms": 50.0,
            "max_duration_ms": 10.0
        }
    
    @pytest.fixture
    def strategy(self, strategy_config):
        """Экземпляр стратегии для тестирования."""
        return BaseSignalsBurstStrategy(strategy_config)
    
    @pytest.fixture
    def base_signals_operation(self):
        """Мок base_signals операции."""
        return SubOperationLog(
            step_number=1,
            operation_name="SET_VALUE",
            target="calculations_data",
            start_time=time.time(),
            caller_info=MockCallerInfo("base_signals.py", 51, "handle_request_cycle"),
            sub_operations=[],  # Атомарная операция
            duration_ms=2.5
        )
    
    @pytest.fixture
    def non_base_signals_operation(self):
        """Мок не-base_signals операции."""
        return SubOperationLog(
            step_number=2,
            operation_name="COMPLEX_OPERATION",
            target="calculations_data", 
            start_time=time.time(),
            caller_info=MockCallerInfo("main_window.py", 446, "complex_method"),
            sub_operations=[Mock()],  # Есть подоперации
            duration_ms=150.0
        )
```

## Модульное тестирование ключевых методов

### Тестирование идентификации операций

```python
    def test_is_base_signals_operation_positive(self, strategy, base_signals_operation):
        """Тест корректной идентификации base_signals операции."""
        assert strategy._is_base_signals_operation(base_signals_operation) is True
    
    def test_is_base_signals_operation_wrong_file(self, strategy, base_signals_operation):
        """Тест отклонения операции из неправильного файла."""
        base_signals_operation.caller_info.filename = "main_window.py"
        assert strategy._is_base_signals_operation(base_signals_operation) is False
    
    def test_is_base_signals_operation_wrong_line(self, strategy, base_signals_operation):
        """Тест отклонения операции с неправильной строкой."""
        base_signals_operation.caller_info.line_number = 100
        assert strategy._is_base_signals_operation(base_signals_operation) is False
    
    def test_is_base_signals_operation_has_sub_operations(self, strategy, base_signals_operation):
        """Тест отклонения операции с подоперациями."""
        base_signals_operation.sub_operations = [Mock()]
        assert strategy._is_base_signals_operation(base_signals_operation) is False
    
    def test_is_base_signals_operation_too_long(self, strategy, base_signals_operation):
        """Тест отклонения слишком долгой операции."""
        base_signals_operation.duration_ms = 50.0  # Больше max_duration_ms=10.0
        assert strategy._is_base_signals_operation(base_signals_operation) is False
```

### Тестирование временной группировки

```python
    def test_group_by_temporal_proximity_simple_burst(self, strategy):
        """Тест группировки простого бурста."""
        base_time = time.time()
        operations = [
            self._create_base_signals_op(1, "SET_VALUE", base_time),
            self._create_base_signals_op(2, "GET_VALUE", base_time + 0.020),  # 20ms gap
            self._create_base_signals_op(3, "UPDATE_VALUE", base_time + 0.040)  # 20ms gap
        ]
        
        clusters = strategy._group_by_temporal_proximity(operations)
        
        assert len(clusters) == 1
        assert len(clusters[0]) == 3
        assert clusters[0] == operations
    
    def test_group_by_temporal_proximity_gap_too_large(self, strategy):
        """Тест разделения бурста при большом разрыве."""
        base_time = time.time()
        operations = [
            self._create_base_signals_op(1, "SET_VALUE", base_time),
            self._create_base_signals_op(2, "GET_VALUE", base_time + 0.020),
            self._create_base_signals_op(3, "UPDATE_VALUE", base_time + 0.120)  # 100ms gap > max_gap
        ]
        
        clusters = strategy._group_by_temporal_proximity(operations)
        
        assert len(clusters) == 1  # Только первые две операции образуют кластер
        assert len(clusters[0]) == 2
        assert clusters[0] == operations[:2]
    
    def test_group_by_temporal_proximity_insufficient_size(self, strategy):
        """Тест отклонения слишком малых кластеров."""
        base_time = time.time()
        operations = [
            self._create_base_signals_op(1, "SET_VALUE", base_time)
        ]
        
        clusters = strategy._group_by_temporal_proximity(operations)
        
        assert len(clusters) == 0  # Одиночная операция не формирует кластер
    
    def _create_base_signals_op(self, step: int, operation: str, timestamp: float) -> SubOperationLog:
        """Вспомогательный метод создания base_signals операции."""
        return SubOperationLog(
            step_number=step,
            operation_name=operation,
            target="calculations_data",
            start_time=timestamp,
            caller_info=MockCallerInfo("base_signals.py", 51, "handle_request_cycle"),
            sub_operations=[],
            duration_ms=2.0
        )
```

### Тестирование detect() метода

```python
    def test_detect_returns_meta_id_for_burst(self, strategy):
        """Тест возврата meta_id для операции в бурсте."""
        base_time = time.time()
        
        # Создание контекста с бурстом
        operations = [
            self._create_base_signals_op(1, "SET_VALUE", base_time),
            self._create_base_signals_op(2, "GET_VALUE", base_time + 0.020),
            self._create_base_signals_op(3, "UPDATE_VALUE", base_time + 0.040)
        ]
        
        context = OperationLog("TEST_OPERATION", sub_operations=operations)
        
        # Тестирование обнаружения для каждой операции
        for op in operations:
            meta_id = strategy.detect(op, context)
            assert meta_id is not None
            assert meta_id.startswith("base_signals_burst_")
            # Все операции должны получить одинаковый meta_id
            assert meta_id == f"base_signals_burst_{int(base_time * 1000)}_0"
    
    def test_detect_returns_none_for_non_base_signals(self, strategy, non_base_signals_operation):
        """Тест возврата None для не-base_signals операции."""
        context = OperationLog("TEST_OPERATION", sub_operations=[non_base_signals_operation])
        
        meta_id = strategy.detect(non_base_signals_operation, context)
        
        assert meta_id is None
    
    def test_detect_returns_none_for_single_operation(self, strategy):
        """Тест возврата None для одиночной операции."""
        base_time = time.time()
        operation = self._create_base_signals_op(1, "SET_VALUE", base_time)
        context = OperationLog("TEST_OPERATION", sub_operations=[operation])
        
        meta_id = strategy.detect(operation, context)
        
        assert meta_id is None  # Одиночные операции не группируются
```
        target_op.sub_operations_count = 0
        target_op.operation_name = "SET_VALUE"
        
        assert self.strategy._is_target_operation(target_op)
        
        # Отрицательные случаи
        non_target_op = Mock()
        non_target_op.caller_info = "other_module.py:10"
        non_target_op.sub_operations_count = 0
        non_target_op.operation_name = "SET_VALUE"
        
        assert not self.strategy._is_target_operation(non_target_op)
```

### Тестирование кластеризации

```python
def test_find_cluster_operations(self):
    """Тест поиска операций для кластера"""
    from datetime import datetime, timedelta
    
    base_time = datetime.now()
    
    # Создание тестовых операций
    op1 = Mock()
    op1.caller_info = "base_signals.py:51"
    op1.sub_operations_count = 0
    op1.operation_name = "SET_VALUE"
    op1.start_time = base_time
    
    op2 = Mock()
    op2.caller_info = "base_signals.py:51"
    op2.sub_operations_count = 0
    op2.operation_name = "GET_VALUE"
    op2.start_time = base_time + timedelta(milliseconds=50)
    
    op3 = Mock()
    op3.caller_info = "base_signals.py:51"
    op3.sub_operations_count = 0
    op3.operation_name = "UPDATE_VALUE"
    op3.start_time = base_time + timedelta(milliseconds=200)  # Вне окна
    
    context = [op1, op2, op3]
    cluster_ops = self.strategy._find_cluster_operations(op1, context)
    
    # Должны быть найдены op1 и op2, но не op3
    assert len(cluster_ops) == 2
    assert op1 in cluster_ops
    assert op2 in cluster_ops
    assert op3 not in cluster_ops

def test_detect_method(self):
    """Тест основного метода detect"""
    # Создание контекста с кластеризуемыми операциями
    operations = self.create_test_operations_cluster()
    target_op = operations[0]
    context = operations
    
    meta_id = self.strategy.detect(target_op, context)
    
    assert meta_id is not None
    assert meta_id.startswith("base_signals_burst_")

def test_detect_insufficient_cluster_size(self):
    """Тест detect при недостаточном размере кластера"""
    # Одиночная операция
    single_op = self.create_single_base_signals_operation()
    
    meta_id = self.strategy.detect(single_op, [single_op])
    
    assert meta_id is None  # Кластер не должен создаваться
```

### Тестирование форматирования

```python
def test_get_meta_operation_description(self):
    """Тест генерации описания мета-операции"""
    operations = self.create_test_operations_cluster()
    meta_id = "test_meta_id"
    
    description = self.strategy.get_meta_operation_description(meta_id, operations)
    
    assert "BaseSignalsBurst:" in description
    assert f"{len(operations)} операции" in description
    assert "мс" in description
    assert "actor:" in description

def test_calculate_duration_ms(self):
    """Тест расчета длительности кластера"""
    from datetime import datetime, timedelta
    
    base_time = datetime.now()
    operations = [
        Mock(start_time=base_time, end_time=base_time + timedelta(milliseconds=1)),
        Mock(start_time=base_time + timedelta(milliseconds=50), 
             end_time=base_time + timedelta(milliseconds=52))
    ]
    
    duration = self.strategy._calculate_duration_ms(operations)
    
    assert duration == 52  # От начала первой до конца последней
```

## Интеграционное тестирование

### Тестирование с MetaOperationDetector

```python
class TestBaseSignalsBurstIntegration:
    
    def test_strategy_registration(self):
        """Тест регистрации стратегии в детекторе"""
        config = MetaOperationConfig()
        detector = MetaOperationDetector(config)
        
        strategy_names = [s.strategy_name for s in detector.strategies]
        assert "BaseSignalsBurst" in strategy_names
    
    def test_strategy_priority(self):
        """Тест приоритета стратегии"""
        config = MetaOperationConfig()
        detector = MetaOperationDetector(config)
        
        # BaseSignalsBurst должна быть первой в списке (высший приоритет)
        first_strategy = detector.strategies[0]
        assert first_strategy.strategy_name == "BaseSignalsBurst"
    
    def test_end_to_end_clustering(self):
        """Тест полного цикла кластеризации"""
        # Создание реалистичных операций
        main_operation = self.create_main_operation_with_base_signals()
        
        # Запуск агрегированного логирования
        logger = AggregatedOperationLogger()
        result = logger.log_operation(main_operation)
        
        # Проверка наличия мета-операций
        assert result.meta_operations is not None
        assert len(result.meta_operations) > 0
        
        # Проверка типа мета-операции
        base_signals_meta = next(
            (mo for mo in result.meta_operations 
             if mo.strategy_name == "BaseSignalsBurst"), 
            None
        )
        assert base_signals_meta is not None
```

### Тестирование конфигурации

```python
def test_configuration_loading(self):
    """Тест загрузки конфигурации"""
    config_data = {
        "base_signals_burst": {
            "enabled": True,
            "window_ms": 150.0,
            "min_cluster_size": 3
        }
    }
    
    config = MetaOperationConfig(config_data)
    strategy_config = config.get_strategy_config("base_signals_burst")
    
    assert strategy_config["window_ms"] == 150.0
    assert strategy_config["min_cluster_size"] == 3

def test_strategy_disable_via_config(self):
    """Тест отключения стратегии через конфигурацию"""
    config_data = {
        "base_signals_burst": {
            "enabled": False
        }
    }
    
    config = MetaOperationConfig(config_data)
    detector = MetaOperationDetector(config)
    
    strategy_names = [s.strategy_name for s in detector.strategies]
    assert "BaseSignalsBurst" not in strategy_names
```

## Тестирование форматирования

### Тестирование OperationTableFormatter

```python
class TestBaseSignalsBurstFormatting:
    
    def test_format_meta_operation(self):
        """Тест форматирования мета-операции"""
        meta_operation = self.create_test_meta_operation()
        formatter = OperationTableFormatter()
        
        formatted_output = formatter.format_meta_operation(meta_operation)
        
        assert "BaseSignals Burst" in formatted_output
        assert ">>> BaseSignals Burst" in formatted_output
        assert "операции" in formatted_output
    
    def test_compact_format(self):
        """Тест компактного формата"""
        meta_operation = self.create_test_meta_operation()
        formatter = OperationTableFormatter(mode="compact")
        
        output = formatter.format_meta_operation(meta_operation)
        
        assert len(output.split('\n')) <= 3  # Компактный вывод
        assert "BaseSignalsBurst:" in output
    
    def test_json_format(self):
        """Тест JSON формата"""
        meta_operation = self.create_test_meta_operation()
        formatter = OperationTableFormatter(mode="json")
        
        json_output = formatter.format_meta_operation(meta_operation)
        
        import json
        parsed = json.loads(json_output)
        assert parsed["strategy_name"] == "BaseSignalsBurst"
        assert "operations" in parsed
```

## Производительное тестирование

### Тестирование больших объемов данных

```python
def test_large_operation_log_performance(self):
    """Тест производительности на больших логах"""
    import time
    
    # Создание большого лога (1000 операций)
    large_context = self.create_large_operation_context(1000)
    target_operation = large_context[500]  # Операция в середине
    
    start_time = time.time()
    meta_id = self.strategy.detect(target_operation, large_context)
    end_time = time.time()
    
    execution_time = end_time - start_time
    assert execution_time < 0.1  # Должно выполняться менее чем за 100мс
    
def test_memory_usage(self):
    """Тест использования памяти"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Выполнение множественных кластеризаций
    for _ in range(100):
        operations = self.create_test_operations_cluster()
        self.strategy.detect(operations[0], operations)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Увеличение памяти не должно превышать 10MB
    assert memory_increase < 10 * 1024 * 1024
```

## Валидационное тестирование

### Тестирование на реальных данных

```python
def test_real_log_data_validation(self):
    """Валидация на реальных данных логов"""
    # Загрузка реального лога операций
    real_log_path = "tests/fixtures/real_operation_log.json"
    operations = self.load_real_operations(real_log_path)
    
    # Применение кластеризации
    clusters = []
    for operation in operations:
        if self.strategy._is_target_operation(operation):
            meta_id = self.strategy.detect(operation, operations)
            if meta_id and meta_id not in [c.meta_id for c in clusters]:
                cluster_ops = self.strategy._find_cluster_operations(operation, operations)
                clusters.append(self.create_meta_operation(meta_id, cluster_ops))
    
    # Валидация результатов
    assert len(clusters) > 0, "Должны быть найдены кластеры в реальных данных"
    
    for cluster in clusters:
        assert len(cluster.operations) >= 2, "Каждый кластер должен содержать минимум 2 операции"
        assert all(op.caller_info == "base_signals.py:51" for op in cluster.operations)

def test_edge_cases(self):
    """Тестирование граничных случаев"""
    # Тест с пустым контекстом
    empty_context = []
    single_op = self.create_single_base_signals_operation()
    
    meta_id = self.strategy.detect(single_op, empty_context)
    assert meta_id is None
    
    # Тест с операциями на границе временного окна
    boundary_operations = self.create_boundary_time_operations()
    target_op = boundary_operations[0]
    
    meta_id = self.strategy.detect(target_op, boundary_operations)
    # Результат зависит от точного времени - может быть как None, так и meta_id
```

## Регрессионное тестирование

### Совместимость с существующими компонентами

```python
def test_existing_functionality_preserved(self):
    """Тест сохранения существующей функциональности"""
    # Проверка что добавление BaseSignalsBurst не нарушает другие стратегии
    config = MetaOperationConfig()
    detector = MetaOperationDetector(config)
    
    # Создание операций для других стратегий
    time_window_operations = self.create_time_window_operations()
    target_cluster_operations = self.create_target_cluster_operations()
    
    # Проверка работы TimeWindowStrategy
    time_window_results = []
    for op in time_window_operations:
        meta_id = detector.detect_meta_operations(op, time_window_operations)
        if meta_id:
            time_window_results.append(meta_id)
    
    assert len(time_window_results) > 0, "TimeWindowStrategy должна работать"
    
    # Проверка работы TargetClusterStrategy
    target_cluster_results = []
    for op in target_cluster_operations:
        meta_id = detector.detect_meta_operations(op, target_cluster_operations)
        if meta_id:
            target_cluster_results.append(meta_id)
    
    assert len(target_cluster_results) > 0, "TargetClusterStrategy должна работать"

def test_no_interference_between_strategies(self):
    """Тест отсутствия интерференции между стратегиями"""
    # Смешанные операции для разных стратегий
    mixed_operations = (
        self.create_test_operations_cluster() +  # Для BaseSignalsBurst
        self.create_time_window_operations() +   # Для TimeWindow
        self.create_target_cluster_operations()  # Для TargetCluster
    )
    
    config = MetaOperationConfig()
    detector = MetaOperationDetector(config)
    
    meta_operations = {}
    for operation in mixed_operations:
        meta_id = detector.detect_meta_operations(operation, mixed_operations)
        if meta_id:
            strategy_name = detector.get_strategy_for_meta_id(meta_id)
            meta_operations[strategy_name] = meta_operations.get(strategy_name, 0) + 1
    
    # Должны быть результаты от всех стратегий
    assert "BaseSignalsBurst" in meta_operations
    assert "TimeWindow" in meta_operations or "TargetCluster" in meta_operations
```

## Автоматизация тестирования

### CI/CD интеграция

```yaml
# .github/workflows/base_signals_burst_tests.yml
name: BaseSignalsBurst Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        poetry install
        
    - name: Run BaseSignalsBurst unit tests
      run: |
        poetry run pytest tests/test_base_signals_burst_strategy.py -v
        
    - name: Run integration tests
      run: |
        poetry run pytest tests/test_base_signals_burst_integration.py -v
        
    - name: Run performance tests
      run: |
        poetry run pytest tests/test_base_signals_burst_performance.py -v
        
    - name: Generate coverage report
      run: |
        poetry run pytest --cov=src.core.log_aggregator.detection_strategies tests/ --cov-report=xml
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

### Мониторинг качества кода

```python
# tests/test_code_quality.py
def test_code_style_compliance():
    """Проверка соответствия стилю кода"""
    import subprocess
    
    result = subprocess.run([
        "flake8", 
        "src/core/log_aggregator/detection_strategies.py",
        "--max-line-length=100"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Style violations: {result.stdout}"

def test_type_hints_coverage():
    """Проверка покрытия type hints"""
    import mypy.api
    
    result = mypy.api.run([
        "src/core/log_aggregator/detection_strategies.py",
        "--strict"
    ])
    
    assert "Success" in result[0], f"Type checking failed: {result[0]}"
```

## Задачи этапа

1. ✅ Создать модульные тесты для BaseSignalsBurstStrategy
2. ✅ Разработать интеграционные тесты с MetaOperationDetector
3. ✅ Добавить тесты форматирования вывода
4. ✅ Создать производительные тесты
5. ✅ Провести валидацию на реальных данных
6. ✅ Обеспечить регрессионное тестирование
7. ✅ Настроить автоматизацию CI/CD
8. ⏳ Выполнить финальную валидацию и оптимизацию

## Критерии готовности

### Покрытие тестами
- **Минимум 95%** покрытие кода BaseSignalsBurstStrategy
- **100%** покрытие публичных методов
- Тестирование всех граничных случаев

### Производительность
- Время выполнения `detect()` < 100мс на 1000 операций
- Потребление памяти < 10MB для 100 кластеризаций
- Отсутствие утечек памяти

### Интеграция
- Совместимость со всеми существующими стратегиями
- Корректная работа в составе полного пайплайна логирования
- Стабильность при различных конфигурациях

### Документация
- Полная документация API
- Примеры использования
- Руководство по настройке

## Заключение

Этап 7 завершает цикл разработки **BaseSignalsMetaBurst**, обеспечивая высокое качество, надежность и производительность реализованной стратегии кластеризации. Комплексное тестирование гарантирует соответствие архитектурным принципам и готовность к продакшн-развертыванию.
