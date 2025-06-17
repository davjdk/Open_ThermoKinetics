# Этап 3: Формирование мета-операции BaseSignalsMetaBurst

## Архитектура мета-операции на основе реальных данных

### Структура данных MetaOperation для BaseSignalsBurst

Мета-операция BaseSignalsBurst соответствует существующей архитектуре MetaOperation и добавляет специфические атрибуты для анализа сигнальных бурстов.

```python
@dataclass  
class MetaOperation:
    """Базовая структура мета-операции (существующая в системе)."""
    meta_id: str                        # Уникальный идентификатор
    strategy_name: str                  # "BaseSignalsBurst"
    operations: List[SubOperationLog]   # Сгруппированные операции
    summary: str                        # Человекочитаемое описание
    
    # Специфические атрибуты для BaseSignalsBurst
    real_actor: Optional[str] = None    # Реальный инициатор (main_window.py:446)
    burst_type: Optional[str] = None    # Тип бурста (Parameter_Update, Add_Reaction, etc.)
    target_distribution: Optional[Dict[str, int]] = None  # Распределение по targets
    temporal_characteristics: Optional[Dict[str, float]] = None  # Временные метрики
```

### Context-Aware Actor Resolution

**Проблема**: операции "base_signals.py:51" скрывают реального инициатора.

**Решение**: извлечение реального актора из thread-local контекста:

```python
def extract_real_actor(context: OperationLog) -> str:
    """Извлечение реального инициатора из контекста операции."""
    if context and context.caller_info:
        filename = context.caller_info.filename
        line_number = context.caller_info.line_number
        return f"{filename}:{line_number}"
    return "base_signals.py:51"  # Fallback

def determine_burst_type(operations: List[SubOperationLog]) -> str:
    """Определение типа бурста на основе паттерна операций."""
    operation_types = [op.operation_name for op in operations]
    
    # Parameter Update pattern: GET_VALUE → CHECK → SET_VALUE → UPDATE_VALUE
    if any("UPDATE_VALUE" in op_types for op_types in [operation_types]):
        return "Parameter_Update_Burst"
    
    # Add Reaction pattern: SET_VALUE → GET_VALUE → UPDATE_VALUE (multiple)
    if operation_types.count("SET_VALUE") >= 2 and "UPDATE_VALUE" in operation_types:
        return "Add_Reaction_Burst"
    
    # Highlight pattern: GET_DF_DATA → GET_VALUE → HIGHLIGHT_*
    if "GET_DF_DATA" in operation_types and any("HIGHLIGHT" in op for op in operation_types):
        return "Highlight_Reaction_Burst"
    
    # Generic burst
    return "Generic_Signal_Burst"
```

### Реалистичные примеры мета-операций

#### Пример 1: Parameter Update Burst
```python
MetaOperation(
    meta_id="base_signals_burst_1718647189445_0",
    strategy_name="BaseSignalsBurst", 
    operations=[
        SubOperationLog(operation_name="GET_VALUE", target="calculations_data", start_time=1718647189.445),
        SubOperationLog(operation_name="CHECK_PATH", target="calculations_data", start_time=1718647189.460),
        SubOperationLog(operation_name="SET_VALUE", target="calculations_data", start_time=1718647189.477),
        SubOperationLog(operation_name="UPDATE_VALUE", target="calculations_data", start_time=1718647189.490)
    ],
    summary="Parameter Update Burst: 4 operations in 45ms",
    real_actor="main_window.py:456",
    burst_type="Parameter_Update_Burst",
    target_distribution={"calculations_data": 4},
    temporal_characteristics={
        "total_duration_ms": 45.0,
        "avg_operation_duration_ms": 11.25,
        "max_gap_ms": 17.0,
        "operations_per_second": 88.9
    }
)
```

#### Пример 2: Multi-target Highlight Burst  
```python
MetaOperation(
    meta_id="base_signals_burst_1718647190188_1",
    strategy_name="BaseSignalsBurst",
    operations=[
        SubOperationLog(operation_name="GET_DF_DATA", target="file_data", start_time=1718647190.188),
        SubOperationLog(operation_name="GET_VALUE", target="calculations_data", start_time=1718647190.193),
        SubOperationLog(operation_name="HIGHLIGHT_REACTION", target="calculations_data", start_time=1718647190.206)
    ],
    summary="Highlight Reaction Burst: 3 operations across 2 targets in 18ms",
    real_actor="main_window.py:446", 
    burst_type="Highlight_Reaction_Burst",
    target_distribution={"file_data": 1, "calculations_data": 2},
    temporal_characteristics={
        "total_duration_ms": 18.0,
        "avg_operation_duration_ms": 6.0,
        "max_gap_ms": 13.0,
        "operations_per_second": 166.7
    }
)
```

### Генерация информативных summary

**Алгоритм создания summary**:
```python
def generate_burst_summary(operations: List[SubOperationLog], 
                          burst_type: str,
                          temporal_chars: Dict[str, float],
                          target_dist: Dict[str, int]) -> str:
    """Генерация информативной сводки для BaseSignals бурста."""
    op_count = len(operations)
    duration_ms = temporal_chars["total_duration_ms"]
    
    # Базовая информация
    base_summary = f"{burst_type}: {op_count} operations in {duration_ms:.1f}ms"
    
    # Дополнительная информация о targets
    if len(target_dist) > 1:
        targets_info = ", ".join([f"{target}({count})" for target, count in target_dist.items()])
        base_summary += f" across {len(target_dist)} targets [{targets_info}]"
    
    # Информация о производительности
    ops_per_sec = temporal_chars.get("operations_per_second", 0)
    if ops_per_sec > 100:
        base_summary += f" ({ops_per_sec:.0f} ops/s)"
    
    return base_summary
```

**Примеры генерируемых summary**:
- `"Parameter Update Burst: 4 operations in 45.0ms"`
- `"Add Reaction Burst: 5 operations in 25.0ms across 1 targets [calculations_data(5)]"`
- `"Highlight Reaction Burst: 3 operations in 18.0ms across 2 targets [file_data(1), calculations_data(2)] (167 ops/s)"`

### Метрики и аналитика

#### Temporal Characteristics
```python
def calculate_temporal_characteristics(operations: List[SubOperationLog]) -> Dict[str, float]:
    """Расчет временных характеристик бурста."""
    if not operations:
        return {}
    
    # Сортировка по времени
    sorted_ops = sorted(operations, key=lambda op: op.start_time)
    
    # Основные метрики
    total_duration = (sorted_ops[-1].start_time - sorted_ops[0].start_time) * 1000  # ms
    avg_op_duration = sum(op.duration_ms for op in operations) / len(operations)
    
    # Вычисление разрывов между операциями
    gaps = [
        (sorted_ops[i].start_time - sorted_ops[i-1].start_time) * 1000 
        for i in range(1, len(sorted_ops))
    ]
    max_gap = max(gaps) if gaps else 0.0
    
    # Операций в секунду
    ops_per_second = len(operations) / (total_duration / 1000) if total_duration > 0 else 0
    
    return {
        "total_duration_ms": total_duration,
        "avg_operation_duration_ms": avg_op_duration,
        "max_gap_ms": max_gap,
        "operations_per_second": ops_per_second
    }
```

#### Target Distribution
```python
def calculate_target_distribution(operations: List[SubOperationLog]) -> Dict[str, int]:
    """Расчет распределения операций по targets."""
    distribution = {}
    for op in operations:
        target = op.target
        distribution[target] = distribution.get(target, 0) + 1
    return distribution
```

## Интеграция в MetaOperationDetector

### Метод get_meta_operation_description()

```python
def get_meta_operation_description(self, meta_id: str, operations: List[SubOperationLog]) -> str:
    """Генерация описания мета-операции для форматтера."""
    burst_type = self._determine_burst_type(operations)
    temporal_chars = self._calculate_temporal_characteristics(operations) 
    target_dist = self._calculate_target_distribution(operations)
    
    # Генерация базовой сводки
    summary = self._generate_burst_summary(operations, burst_type, temporal_chars, target_dist)
    
    # Добавление контекстной информации
    context = get_current_operation_logger()
    if context and context.current_operation:
        real_actor = self._extract_real_actor(context.current_operation)
        summary += f" (initiated by {real_actor})"
    
    return summary
```

### Стабильная генерация meta_id

```python
def _generate_stable_meta_id(self, operations: List[SubOperationLog], cluster_index: int = 0) -> str:
    """Генерация стабильного идентификатора мета-операции."""
    if not operations:
        return f"base_signals_burst_empty_{cluster_index}"
    
    # Используем timestamp первой операции + индекс кластера
    first_op = min(operations, key=lambda op: op.start_time)
    timestamp_ms = int(first_op.start_time * 1000)
    
    return f"base_signals_burst_{timestamp_ms}_{cluster_index}"
```

## Результаты этапа 3

### ✅ Завершенные задачи

1. **✅ Адаптация к существующей архитектуре MetaOperation**: использование стандартной структуры данных

2. **✅ Context-Aware Actor Resolution**: извлечение реального инициатора из thread-local контекста

3. **✅ Классификация типов бурстов**: Parameter_Update, Add_Reaction, Highlight_Reaction, Generic

4. **✅ Расширенные аналитические метрики**: temporal_characteristics, target_distribution

5. **✅ Информативная система summary**: адаптивное описание с контекстной информацией

### 🎯 Ключевые достижения

**Полная интеграция**: структура мета-операций соответствует существующей архитектуре без нарушения совместимости.

**Аналитическая ценность**: метрики предоставляют данные для архитектурной оптимизации и производительностного анализа.

**Контекстная осведомленность**: восстановление связи между низкоуровневыми сигналами и высокоуровневыми пользовательскими действиями.

### 🚀 Готовность к этапу 4

Структура мета-операций полностью спроектирована. Все методы и алгоритмы готовы к реализации в BaseSignalsBurstStrategy классе.

---

*Этап 3 завершён: 17 июня 2025*  
*Статус: Готов к реализации стратегии*  
*Следующий этап: [STAGE_04_STRATEGY_IMPLEMENTATION.md](STAGE_04_STRATEGY_IMPLEMENTATION.md)*
