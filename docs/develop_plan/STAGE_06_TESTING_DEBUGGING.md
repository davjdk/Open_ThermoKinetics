# Этап 6: Тестирование и отладка

## Цель этапа
Создать комплексную систему тестирования для BaseSignalsBurstStrategy, включая unit-тесты, интеграционные тесты и отладочные инструменты.

## Задачи

### 6.1 Unit-тесты для стратегии кластеризации

**Создание test_base_signals_burst_strategy.py:**

```python
import pytest
from unittest.mock import Mock, patch
from src.core.log_aggregator.detection_strategies import BaseSignalsBurstStrategy
from src.core.log_aggregator.sub_operation_log import SubOperationLog
from src.core.log_aggregator.operation_log import OperationLog


class TestBaseSignalsBurstStrategy:
    
    @pytest.fixture
    def strategy_config(self):
        """Базовая конфигурация стратегии."""
        return {
            "window_ms": 100.0,
            "min_cluster_size": 2,
            "include_noise": True,
            "max_cluster_duration_ms": 5000,
        }
    
    @pytest.fixture
    def strategy(self, strategy_config):
        """Экземпляр стратегии с базовой конфигурацией."""
        return BaseSignalsBurstStrategy(strategy_config)
    
    def test_strategy_name(self, strategy):
        """Тест имени стратегии."""
        assert strategy.strategy_name == "BaseSignalsBurst"
    
    def test_validate_config_valid(self, strategy):
        """Тест валидации корректной конфигурации."""
        # Не должно вызывать исключений
        strategy.validate_config()
    
    def test_validate_config_missing_params(self):
        """Тест валидации с отсутствующими параметрами."""
        incomplete_config = {"window_ms": 100.0}  # Отсутствует min_cluster_size
        
        with pytest.raises(ValueError, match="missing required parameter"):
            strategy = BaseSignalsBurstStrategy(incomplete_config)
            strategy.validate_config()
    
    def test_validate_config_invalid_values(self):
        """Тест валидации с некорректными значениями."""
        invalid_configs = [
            {"window_ms": -10, "min_cluster_size": 2},      # Отрицательное окно
            {"window_ms": 100, "min_cluster_size": 0},      # Нулевой размер кластера
            {"window_ms": "invalid", "min_cluster_size": 2}, # Неверный тип
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValueError):
                strategy = BaseSignalsBurstStrategy(config)
                strategy.validate_config()
    
    def test_is_base_signals_operation(self, strategy):
        """Тест определения base_signals операций."""
        # Операция base_signals
        base_signals_op = SubOperationLog(
            step_number=1,
            operation_name="SIGNAL_FETCH",
            target="base_signals",
            start_time=1.0
        )
        assert strategy._is_base_signals_operation(base_signals_op) == True
        
        # Операция не base_signals
        other_op = SubOperationLog(
            step_number=2,
            operation_name="LOAD_FILE",
            target="file_data",
            start_time=1.1
        )
        assert strategy._is_base_signals_operation(other_op) == False
        
        # Операция с сигналом в названии
        signal_op = SubOperationLog(
            step_number=3,
            operation_name="REQUEST_SIGNAL",
            target="calculation_data",
            start_time=1.2
        )
        assert strategy._is_base_signals_operation(signal_op) == True
    
    def test_generate_cluster_id(self, strategy):
        """Тест генерации ID кластера."""
        operation = SubOperationLog(
            step_number=5,
            operation_name="SIGNAL_FETCH",
            target="base_signals",
            start_time=1234.567
        )
        
        cluster_id = strategy._generate_cluster_id(operation)
        
        # Проверяем формат ID
        assert cluster_id.startswith("base_signals_burst_")
        assert "1234567" in cluster_id  # timestamp * 1000
        assert "5" in cluster_id        # step_number
    
    def test_calculate_duration_ms(self, strategy):
        """Тест вычисления длительности кластера."""
        operations = [
            SubOperationLog(1, "OP1", "target1", 1.0, 1.05),  # 50ms
            SubOperationLog(2, "OP2", "target2", 1.02, 1.08), # 60ms, но границы 1.0-1.08 = 80ms
        ]
        
        duration = strategy._calculate_duration_ms(operations)
        assert duration == 80  # 0.08 секунд = 80 мс
    
    def test_find_time_window_cluster(self, strategy):
        """Тест поиска операций в временном окне."""
        # Создаем операции для тестирования
        operations = [
            SubOperationLog(1, "SIGNAL_1", "base_signals", 1.0),      # base_signals
            SubOperationLog(2, "LOAD_FILE", "file_data", 1.02),       # шум
            SubOperationLog(3, "SIGNAL_2", "base_signals", 1.05),     # base_signals  
            SubOperationLog(4, "CALC", "calculation", 1.15),          # вне окна
            SubOperationLog(5, "SIGNAL_3", "base_signals", 1.18),     # вне окна
        ]
        
        context = Mock(spec=OperationLog)
        context.sub_operations = operations
        
        # Тестируем кластеризацию первой операции (должна захватить операции 1, 2, 3)
        cluster = strategy._find_time_window_cluster(operations[0], context, 0.1)  # 100ms
        
        assert len(cluster) == 3
        assert cluster[0].step_number == 1  # SIGNAL_1
        assert cluster[1].step_number == 2  # LOAD_FILE (шум)
        assert cluster[2].step_number == 3  # SIGNAL_2
```

### 6.2 Интеграционные тесты

**Тест полного цикла кластеризации:**

```python
def test_full_clustering_cycle(self, strategy):
    """Тест полного цикла обнаружения и кластеризации."""
    # Создаем набор операций с паттерном base_signals burst
    operations = [
        SubOperationLog(1, "SIGNAL_REQUEST", "base_signals", 1.0, 1.01),
        SubOperationLog(2, "GET_VALUE", "calc_data", 1.015, 1.02),    # шум
        SubOperationLog(3, "SIGNAL_RESPONSE", "base_signals", 1.03, 1.035),
        SubOperationLog(4, "UPDATE_VALUE", "calc_data", 1.04, 1.045), # шум
        SubOperationLog(5, "SIGNAL_EMIT", "base_signals", 1.05, 1.055),
        SubOperationLog(6, "UNRELATED_OP", "other_module", 2.0, 2.01), # вне окна
    ]
    
    context = OperationLog(
        operation_id=1,
        operation_name="TEST_OPERATION",
        start_time=1.0,
        sub_operations=operations
    )
    
    # Тестируем detect для каждой операции base_signals
    base_signals_ops = [op for op in operations if strategy._is_base_signals_operation(op)]
    
    detected_clusters = []
    for op in base_signals_ops:
        cluster_id = strategy.detect(op, context)
        if cluster_id:
            detected_clusters.append(cluster_id)
    
    # Все base_signals операции должны получить одинаковый cluster_id
    assert len(set(detected_clusters)) == 1
    assert len(detected_clusters) == 3  # Три base_signals операции
    
    # Операция вне временного окна не должна быть включена
    far_cluster = strategy.detect(operations[5], context)
    assert far_cluster is None or far_cluster != detected_clusters[0]

def test_description_generation(self, strategy):
    """Тест генерации описания кластера."""
    operations = [
        SubOperationLog(1, "SIGNAL_1", "base_signals", 1.0, 1.01, 
                       request_kwargs={"actor": "gui_component"}),
        SubOperationLog(2, "LOAD_DATA", "file_data", 1.02, 1.025),  # шум
        SubOperationLog(3, "SIGNAL_2", "base_signals", 1.03, 1.035),
    ]
    
    meta_id = "base_signals_burst_1000_1"
    description = strategy.get_meta_operation_description(meta_id, operations)
    
    # Проверяем формат описания
    assert "BaseSignalsBurst" in description
    assert "3 операций" in description
    assert "мс" in description
    assert "actor:" in description
    assert "шум:" in description
```

### 6.3 Тесты граничных случаев

```python
def test_edge_cases(self, strategy):
    """Тест граничных случаев."""
    
    # Тест с операциями без времени
    no_time_ops = [
        SubOperationLog(1, "SIGNAL_1", "base_signals", None),
        SubOperationLog(2, "SIGNAL_2", "base_signals", None),
    ]
    context = Mock(spec=OperationLog)
    context.sub_operations = no_time_ops
    
    # Не должно вызывать исключений
    cluster_id = strategy.detect(no_time_ops[0], context)
    # Может вернуть None или обработать gracefully
    
    # Тест с одной операцией (меньше min_cluster_size)
    single_op = [SubOperationLog(1, "SIGNAL_1", "base_signals", 1.0)]
    context.sub_operations = single_op
    
    cluster_id = strategy.detect(single_op[0], context)
    assert cluster_id is None  # Меньше минимального размера
    
    # Тест с очень большим временным окном
    strategy.config["window_ms"] = 10000  # 10 секунд
    wide_ops = [
        SubOperationLog(1, "SIGNAL_1", "base_signals", 1.0),
        SubOperationLog(2, "SIGNAL_2", "base_signals", 5.0),  # 4 секунды разница
    ]
    context.sub_operations = wide_ops
    
    cluster_id = strategy.detect(wide_ops[0], context)
    assert cluster_id is not None  # Должно находиться в широком окне
```

### 6.4 Отладочные инструменты

**Добавление отладочного режима в стратегию:**

```python
def _debug_log(self, message: str, data: Any = None) -> None:
    """
    Логирование отладочной информации.
    
    Args:
        message: Сообщение для логирования
        data: Дополнительные данные (опционально)
    """
    if self.config.get("debug_mode", False):
        logger.debug(f"BaseSignalsBurstStrategy: {message}")
        if data is not None:
            logger.debug(f"  Data: {data}")

def detect(self, sub_op: SubOperationLog, context: OperationLog) -> Optional[str]:
    """Расширенный detect с отладочной информацией."""
    self._debug_log(f"Analyzing operation {sub_op.step_number}: {sub_op.operation_name}")
    
    if not self._is_base_signals_operation(sub_op):
        self._debug_log("  -> Not a base_signals operation, skipping")
        return None
    
    self._debug_log("  -> Is base_signals operation, searching for cluster")
    
    window_seconds = self.config["window_ms"] / 1000.0
    cluster_operations = self._find_time_window_cluster(sub_op, context, window_seconds)
    
    self._debug_log(f"  -> Found {len(cluster_operations)} operations in time window")
    
    # ... остальная логика с добавлением отладочных сообщений ...
```

### 6.5 Тесты производительности

```python
def test_performance_large_operation_log(self, strategy):
    """Тест производительности на больших логах операций."""
    import time
    
    # Создаем большой лог с 1000 операций
    large_operations = []
    current_time = 1.0
    
    for i in range(1000):
        # Каждая 10-я операция - base_signals
        if i % 10 == 0:
            op = SubOperationLog(i, "SIGNAL_OP", "base_signals", current_time, current_time + 0.01)
        else:
            op = SubOperationLog(i, "OTHER_OP", "other_module", current_time, current_time + 0.005)
        
        large_operations.append(op)
        current_time += 0.01
    
    context = OperationLog(
        operation_id=1,
        operation_name="LARGE_TEST",
        start_time=1.0,
        sub_operations=large_operations
    )
    
    # Измеряем время выполнения
    start_time = time.time()
    
    detected_clusters = 0
    for op in large_operations:
        if strategy._is_base_signals_operation(op):
            cluster_id = strategy.detect(op, context)
            if cluster_id:
                detected_clusters += 1
    
    execution_time = time.time() - start_time
    
    # Проверяем, что выполнение заняло разумное время (< 1 секунды)
    assert execution_time < 1.0
    assert detected_clusters > 0
    
    print(f"Processed {len(large_operations)} operations in {execution_time:.3f}s")
    print(f"Detected {detected_clusters} clustered operations")
```

### 6.6 Мок-тесты интеграции с форматтером

```python
def test_formatter_integration(self, strategy):
    """Тест интеграции с форматтером."""
    from src.core.log_aggregator.table_formatter import BaseSignalsBurstFormatter
    
    operations = [
        SubOperationLog(1, "SIGNAL_1", "base_signals", 1.0, 1.01),
        SubOperationLog(2, "NOISE_OP", "other_module", 1.02, 1.025),
        SubOperationLog(3, "SIGNAL_2", "base_signals", 1.03, 1.035),
    ]
    
    # Создаем мок мета-операции
    meta_operation = Mock()
    meta_operation.meta_id = "base_signals_burst_1000_1"
    meta_operation.description = "BaseSignalsBurst: 3 операций, 35 мс, actor: test, шум: есть"
    meta_operation.sub_operations = operations
    
    # Тестируем форматтер
    formatter_config = {
        "show_noise_markers": True,
        "noise_marker": "[*]",
        "show_detailed_summary": True,
    }
    
    burst_formatter = BaseSignalsBurstFormatter(formatter_config)
    
    # Проверяем, что форматтер корректно обрабатывает кластер
    # (детальная проверка будет в тестах форматтера)
    assert burst_formatter.config["noise_marker"] == "[*]"
    assert burst_formatter.show_noise_markers == True
```

## Результат этапа
- Комплексная система unit-тестов для всех методов стратегии
- Интеграционные тесты полного цикла кластеризации
- Тесты граничных случаев и обработки ошибок
- Отладочные инструменты для диагностики проблем
- Тесты производительности для больших логов
- Мок-тесты интеграции с другими компонентами

## Файлы для создания
- `tests/test_base_signals_burst_strategy.py` - основные unit-тесты
- `tests/test_base_signals_integration.py` - интеграционные тесты
- `tests/test_base_signals_performance.py` - тесты производительности

## Критерии готовности
- [ ] Все unit-тесты проходят успешно
- [ ] Покрытие кода тестами > 90%
- [ ] Интеграционные тесты подтверждают корректную работу
- [ ] Граничные случаи обрабатываются без ошибок
- [ ] Производительность на больших данных приемлема
- [ ] Отладочные инструменты помогают в диагностике
