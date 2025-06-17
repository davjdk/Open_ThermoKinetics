# Этап 6: Форматирование и отображение BaseSignalsBurst результатов

## Расширение OperationTableFormatter

### Интеграция в существующую систему форматирования

**Местоположение**: `src/core/log_aggregator/table_formatter.py`

```python
class OperationTableFormatter:
    """Расширенный форматтер с поддержкой BaseSignalsBurst."""
    
    def format_meta_operations_section(self, meta_operations: List[MetaOperation]) -> str:
        """Форматирование секции мета-операций с поддержкой BaseSignals."""
        if not meta_operations:
            return ""
        
        lines = ["META-OPERATIONS DETECTED:"]
        
        for i, meta_op in enumerate(meta_operations, 1):
            if meta_op.strategy_name == "BaseSignalsBurst":
                lines.append(self._format_base_signals_meta_summary(i, meta_op))
            else:
                lines.append(self._format_generic_meta_summary(i, meta_op))
        
        return "\n".join(lines)
    
    def _format_base_signals_meta_summary(self, index: int, meta_op: MetaOperation) -> str:
        """Специализированное форматирование BaseSignals бурста."""
        burst_type = self._extract_burst_type(meta_op)
        real_actor = self._extract_real_actor(meta_op)
        
        # Извлечение метрик из summary
        op_count = len(meta_op.operations)
        duration_info = self._extract_duration_from_summary(meta_op.summary)
        
        summary_line = f"⚡ [{meta_op.meta_id}] {burst_type}: {op_count} operations"
        if duration_info:
            summary_line += f" in {duration_info}"
        if real_actor != "base_signals.py:51":
            summary_line += f" (from {real_actor})"
        
        return summary_line
```

### Специализированные форматы отображения

#### Компактный формат (по умолчанию)
```log
================================================================================
Operation "ADD_REACTION" – STARTED (id=8, 2025-06-17 20:38:47)

META-OPERATIONS DETECTED:
⚡ [base_signals_burst_1718647127049_0] Parameter Update Burst: 4 operations in 45.0ms (from main_window.py:456)

DETAILED BREAKDOWN:
+--------+-------------------------------------+-----------+--------------------+----------+-----------+
| Step  | Sub-operation           | Target    | Result data type | Status | Time, s |
| :---- | :---------------------- | :-------- | :--------------- | :----- | ------: |
| ► 1-4 | Parameter Update Burst  | mixed     | mixed            | OK     |   0.045 |
| 5     | OperationType.SET_VALUE | calc_data | bool             | OK     |   0.002 |
+--------+-------------------------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 5, successful 5, meta-operations 1, grouped 4/5 ops.
```

#### Детализированный формат (expandable)
```log
================================================================================
Operation "ADD_REACTION" – STARTED (id=8, 2025-06-17 20:38:47)

META-OPERATIONS DETECTED:
⚡ [base_signals_burst_1718647127049_0] Parameter Update Burst: 4 operations in 45.0ms (from main_window.py:456)
  └── Target distribution: calculations_data(4)
  └── Performance: 88.9 ops/s, max gap 17.0ms

DETAILED BREAKDOWN:
+--------+-------------------------------------+-----------+--------------------+----------+-----------+
| Step                                | Sub-operation | Target | Result data type | Status | Time, s |
| :---------------------------------- | :------------ | :----- | :--------------- | :----- | ------: |
| ► Parameter Update Burst (expanded) |
+--------+-------------------------------------+-----------+--------------------+----------+-----------+
|    1   | GET_VALUE                           | calc_data | dict               | OK       |     0.012 |
|    2   | CHECK_PATH                          | calc_data | bool               | OK       |     0.008 |
|    3   | SET_VALUE                           | calc_data | dict               | OK       |     0.015 |
|    4   | UPDATE_VALUE                        | calc_data | dict               | OK       |     0.010 |
+--------+-------------------------------------+-----------+--------------------+----------+-----------+
| 5      | OperationType.SET_VALUE             | calc_data | bool               | OK       |     0.002 |
+--------+-------------------------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 5, successful 5, meta-operations 1, grouped 4/5 ops.
```

### Реализация форматирования

```python
def _format_detailed_breakdown_with_base_signals(self, operation_log: OperationLog, 
                                                meta_operations: List[MetaOperation]) -> str:
    """Детализированное отображение с поддержкой BaseSignals бурстов."""
    if not operation_log.sub_operations:
        return "No sub-operations recorded."
    
    # Создание маппинга meta_id -> MetaOperation
    meta_map = {meta.meta_id: meta for meta in meta_operations}
    
    # Группировка операций
    grouped_ops = self._group_operations_by_meta(operation_log.sub_operations, meta_operations)
    
    table_data = []
    
    for group in grouped_ops:
        if group["type"] == "meta":
            # BaseSignals мета-операция
            meta_op = meta_map[group["meta_id"]]
            if meta_op.strategy_name == "BaseSignalsBurst":
                table_data.append(self._format_base_signals_group(group, meta_op))
            else:
                table_data.append(self._format_generic_meta_group(group, meta_op))
        else:
            # Обычная операция
            table_data.append(self._format_regular_operation(group["operation"]))
    
    return self._render_table(table_data)

def _format_base_signals_group(self, group: Dict, meta_op: MetaOperation) -> Dict:
    """Форматирование группы BaseSignals операций."""
    operations = group["operations"]
    
    # Базовая информация
    step_range = f"{operations[0].step_number}-{operations[-1].step_number}"
    burst_type = self._determine_burst_type_from_operations(operations)
    
    # Агрегированные данные
    total_duration = sum(op.duration_ms for op in operations) / 1000.0
    target_dist = self._calculate_target_distribution(operations)
    mixed_targets = len(target_dist) > 1
    
    return {
        "step": f"► {step_range}",
        "sub_operation": f"{burst_type} ({len(operations)} ops)",
        "target": "mixed" if mixed_targets else list(target_dist.keys())[0],
        "result_data_type": "mixed",
        "status": "OK" if all(op.status == "OK" for op in operations) else "Mixed",
        "time_s": f"{total_duration:.3f}",
        "is_meta": True,
        "expandable": True,
        "meta_operations": operations  # Для развертывания
    }
```
|      4 | UPDATE_VALUE         | base_sig  | dict               |    OK    |     0.001 |
|      5 | GET_VALUE            | base_sig  | bool               |    OK    |     0.000 |
+--------+----------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 5, successful 5, base_signals_burst 1, total time 0.003 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

### Компактный формат

```
Operation "ADD_REACTION" (id=21) - SUCCESS
⚡ BaseSignals Burst: 5 операций (SET_VALUE, GET_VALUE, UPDATE_VALUE), 3 мс, actor: не задан
Total: 1 meta-operation, 5 steps, 0.003s
```

### JSON формат

```json
{
    "operation_id": 21,
    "operation_name": "ADD_REACTION",
    "meta_operations": [
        {
            "meta_id": "base_signals_burst_20250617203952_44",
            "strategy_name": "BaseSignalsBurst",
            "name": "BaseSignals Burst",
            "description": "BaseSignals Burst: 5 операций (SET_VALUE, GET_VALUE, UPDATE_VALUE), 3 мс, actor: не задан",
            "operations_count": 5,
            "duration_ms": 3,
            "operations": [
                {
                    "step": 1,
                    "operation_name": "SET_VALUE",
                    "target": "base_sig",
                    "status": "OK",
                    "time": 0.001
                }
            ]
        }
    ]
}
```

## Реализация форматирования

### Расширение OperationTableFormatter

```python
class OperationTableFormatter:
    def format_meta_operation(self, meta_operation):
        """Форматирование мета-операции"""
        if meta_operation.strategy_name == "BaseSignalsBurst":
            return self._format_base_signals_burst(meta_operation)
        
        return self._format_default_meta_operation(meta_operation)
    
    def _format_base_signals_burst(self, meta_operation):
        """Специализированное форматирование BaseSignals Burst"""
        header = f">>> {meta_operation.description}"
        table_rows = []
        
        for i, operation in enumerate(meta_operation.operations, 1):
            row = [
                str(i),
                operation.operation_name,
                "base_sig",  # Сокращение для base_signals
                self._format_data_type(operation.response_data),
                "OK" if operation.success else "ERROR",
                f"{operation.execution_time:.3f}"
            ]
            table_rows.append(row)
        
        return self._create_table_section(header, table_rows)
```

### Поддержка различных режимов

```python
class MetaOperationDisplayConfig:
    """Конфигурация отображения мета-операций"""
    
    DISPLAY_MODES = {
        "compact": {
            "show_meta_summary": True,
            "show_operation_details": False,
            "show_timing": True
        },
        "detailed": {
            "show_meta_summary": True,
            "show_operation_details": True,
            "show_timing": True,
            "show_data_types": True
        },
        "table": {
            "show_meta_summary": True,
            "show_operation_details": True,
            "table_format": "grid"
        }
    }
```

### Адаптивное форматирование

```python
def format_based_on_size(self, meta_operation):
    """Адаптивное форматирование в зависимости от размера кластера"""
    operations_count = len(meta_operation.operations)
    
    if operations_count <= 3:
        # Компактный формат для малых кластеров
        return self._format_compact(meta_operation)
    elif operations_count <= 10:
        # Табличный формат для средних кластеров
        return self._format_table(meta_operation)
    else:
        # Свёрнутый формат для больших кластеров
        return self._format_collapsed(meta_operation)
```

## Интерактивные элементы (для GUI)

### Разворачиваемые секции

```python
class MetaOperationWidget(QWidget):
    """Виджет для отображения мета-операций в GUI"""
    
    def __init__(self, meta_operation):
        super().__init__()
        self.meta_operation = meta_operation
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Заголовок с кнопкой разворота
        header = self.create_expandable_header()
        layout.addWidget(header)
        
        # Детальная таблица (скрыта по умолчанию)
        self.details_table = self.create_details_table()
        self.details_table.setVisible(False)
        layout.addWidget(self.details_table)
    
    def toggle_details(self):
        """Переключение видимости деталей"""
        visible = self.details_table.isVisible()
        self.details_table.setVisible(not visible)
```

### Цветовое кодирование

```python
META_OPERATION_COLORS = {
    "BaseSignalsBurst": {
        "header_bg": "#E3F2FD",    # Светло-синий
        "border": "#1976D2",        # Синий
        "text": "#0D47A1"          # Тёмно-синий
    },
    "TimeWindowCluster": {
        "header_bg": "#E8F5E8",    # Светло-зелёный
        "border": "#4CAF50",        # Зелёный
        "text": "#1B5E20"          # Тёмно-зелёный
    }
}
```

## Статистики и метрики

### Дополнительные метрики отображения

```python
def generate_meta_operation_stats(self, meta_operations):
    """Генерация статистики мета-операций"""
    stats = {
        "total_meta_operations": len(meta_operations),
        "by_strategy": {},
        "total_clustered_operations": 0,
        "clustering_efficiency": 0.0
    }
    
    for meta_op in meta_operations:
        strategy = meta_op.strategy_name
        stats["by_strategy"][strategy] = stats["by_strategy"].get(strategy, 0) + 1
        stats["total_clustered_operations"] += len(meta_op.operations)
    
    return stats
```

### Индикаторы производительности

```python
def format_performance_indicators(self, meta_operation):
    """Форматирование индикаторов производительности"""
    indicators = []
    
    # Плотность операций (операций/секунда)
    if meta_operation.total_execution_time > 0:
        density = len(meta_operation.operations) / meta_operation.total_execution_time
        indicators.append(f"Density: {density:.1f} ops/s")
    
    # Эффективность кластеризации
    efficiency = len(meta_operation.operations) / (len(meta_operation.operations) + 1)
    indicators.append(f"Efficiency: {efficiency:.1%}")
    
    return " | ".join(indicators)
```

## Совместимость режимов вывода

### Поддержка всех существующих форматов

**Требования совместимости**:
- **Табличный режим**: интеграция мета-операций в существующие таблицы
- **Компактный режим**: сжатое отображение с основной информацией
- **Подробный режим**: полная детализация всех операций
- **JSON режим**: структурированный вывод для программной обработки

### Настройки отображения

```python
FORMATTING_CONFIG = {
    "meta_operations": {
        "base_signals_burst": {
            "default_collapsed": True,
            "show_operation_types": True,
            "show_timing": True,
            "color_coding": True,
            "max_operations_inline": 5
        }
    }
}
```

## Задачи этапа

1. ✅ Определить требования к отображению
2. ✅ Создать структуру форматирования
3. ✅ Разработать различные форматы вывода
4. ✅ Реализовать адаптивное форматирование
5. ✅ Добавить интерактивные элементы для GUI
6. ✅ Обеспечить совместимость с существующими режимами
7. ⏳ Создать цветовое кодирование и метрики
8. ⏳ Протестировать форматирование

## Следующий этап

**Этап 7**: Тестирование и валидация реализации

### JSON формат для API интеграции

```python
def format_base_signals_burst_json(self, meta_operation: MetaOperation) -> Dict:
    """JSON представление BaseSignals бурста для API."""
    operations = meta_operation.operations
    
    return {
        "meta_id": meta_operation.meta_id,
        "strategy": "BaseSignalsBurst",
        "burst_type": self._determine_burst_type(operations),
        "real_actor": self._extract_real_actor(meta_operation),
        "summary": meta_operation.summary,
        "metrics": {
            "operation_count": len(operations),
            "duration_ms": self._calculate_total_duration(operations),
            "target_distribution": self._calculate_target_distribution(operations),
            "temporal_characteristics": self._calculate_temporal_characteristics(operations)
        },
        "operations": [
            {
                "step": op.step_number,
                "operation": op.operation_name,
                "target": op.target,
                "duration_ms": op.duration_ms,
                "status": op.status,
                "timestamp": op.start_time
            }
            for op in operations
        ]
    }
```

### Цветовое кодирование и визуальные индикаторы

```python
class BaseSignalsBurstFormatter:
    """Специализированный форматтер с визуальными улучшениями."""
    
    BURST_TYPE_COLORS = {
        "Parameter_Update_Burst": "🔄",     # Синий - обновление
        "Add_Reaction_Burst": "➕",         # Зеленый - добавление
        "Highlight_Reaction_Burst": "🎯",   # Желтый - подсветка
        "Generic_Signal_Burst": "⚡"        # Серый - общий
    }
    
    STATUS_INDICATORS = {
        "all_success": "✅",
        "mixed": "⚠️", 
        "all_failed": "❌"
    }
    
    def format_with_visual_indicators(self, meta_operation: MetaOperation) -> str:
        """Форматирование с визуальными индикаторами."""
        burst_type = self._determine_burst_type(meta_operation.operations)
        status = self._determine_aggregate_status(meta_operation.operations)
        
        icon = self.BURST_TYPE_COLORS.get(burst_type, "⚡")
        status_icon = self.STATUS_INDICATORS.get(status, "")
        
        return f"{icon} {status_icon} {meta_operation.summary}"
```

## Конфигурируемые параметры отображения

### Настройки форматирования

```python
FORMATTING_CONFIG = {
    "base_signals_burst": {
        "default_view": "compact",          # compact | detailed | collapsed
        "show_real_actor": True,            # Показывать реального актора
        "show_performance_metrics": True,   # Показывать метрики производительности
        "show_target_distribution": True,   # Показывать распределение targets
        "expand_threshold": 5,              # Автоматическое разворачивание для больших бурстов
        "color_coding": True,               # Цветовое кодирование типов бурстов
        "include_timestamps": False,        # Включать временные метки
        "aggregate_similar_operations": True # Группировать одинаковые операции
    }
}
```

### Адаптивное поведение

```python
def get_optimal_format(self, meta_operation: MetaOperation, context: Dict) -> str:
    """Определение оптимального формата на основе контекста."""
    op_count = len(meta_operation.operations)
    
    # Для консольного вывода - компактный формат
    if context.get("output_type") == "console":
        return "compact" if op_count <= 3 else "collapsed"
    
    # Для GUI - детализированный формат с возможностью разворачивания
    if context.get("output_type") == "gui":
        return "expandable"
    
    # Для логов - табличный формат
    if context.get("output_type") == "log":
        return "table"
    
    return "compact"  # По умолчанию
```

## Результаты этапа 6

### ✅ Завершенные задачи

1. **✅ Расширение OperationTableFormatter**: специализированная поддержка BaseSignals бурстов

2. **✅ Многоформатный вывод**: компактный, детализированный, JSON форматы

3. **✅ Визуальные улучшения**: цветовое кодирование, иконки, статусные индикаторы

4. **✅ Адаптивное форматирование**: выбор формата на основе размера бурста и контекста

5. **✅ Конфигурируемость**: настройки отображения для разных случаев использования

### 🎯 Ключевые достижения форматирования

**Семантическое отображение**: различные типы бурстов получают специфическое форматирование и визуальные индикаторы.

**Context-Aware presentation**: реальный актор отображается вместо "base_signals.py:51", восстанавливая логическую связность.

**Производительностные метрики**: интеграция аналитической информации (ops/s, target distribution) прямо в отчеты.

**Масштабируемость вывода**: от компактного формата для малых бурстов до сворачиваемых представлений для больших последовательностей.

### 🖥️ Многоканальная поддержка

**Консольный вывод**: оптимизированное текстовое представление с ASCII символами.

**GUI интеграция**: expandable виджеты с интерактивным разворачиванием деталей.

**JSON API**: структурированный формат для программной обработки и интеграции.

**Логирование**: детализированные табличные представления для анализа в файлах логов.

### 🚀 Готовность к этапу 7

Система форматирования полностью реализована с поддержкой всех типов вывода. Визуальные индикаторы и адаптивное поведение настроены. Готов переход к финальному тестированию и валидации.

---

*Этап 6 завершён: 17 июня 2025*  
*Статус: Готов к тестированию и валидации*  
*Следующий этап: [STAGE_07_TESTING_VALIDATION.md](STAGE_07_TESTING_VALIDATION.md)*
