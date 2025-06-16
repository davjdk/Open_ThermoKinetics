# Этап 5: Форматирование и визуализация метаопераций

## Подходы к форматированию метаопераций

Отдельным аспектом является представление кластеризованных метаопераций в конечном табличном логе. В текущей реализации `OperationTableFormatter` строит плоскую таблицу: колонками "Step", "Sub-operation", "Target", и т.д., построчно перечисляя все операции. После внедрения групп потребуется изменить способ вывода, чтобы визуально отразить кластеризацию.

### Опциональность форматирования

В требованиях указано, что визуальная группировка – опциональна. Это значит, что возможно на первом этапе модуль просто идентифицирует группы (чтобы аналитики могли их увидеть в сыром виде, например, через отладочный вывод или JSON-экспорт), а изменение собственно текстового лога может быть выполнено позднее или по флагу.

## Модификация OperationTableFormatter

### Расширение конфигурации форматтера

```python
# В src/core/log_aggregator/table_formatter.py

@dataclass
class FormatterConfig:
    """Конфигурация форматтера с поддержкой метаопераций"""
    
    # Существующие параметры
    table_format: str = "grid"
    max_cell_width: int = 50
    
    # Новые параметры для метаопераций
    group_meta_operations: bool = True          # Включить группировку в выводе
    compact_meta_view: bool = True              # Компактное отображение групп
    show_individual_ops: bool = False           # Показывать отдельные операции внутри групп
    max_operations_inline: int = 5              # Максимум операций для inline отображения
    meta_operation_symbol: str = "►"            # Символ для обозначения метаопераций
    indent_size: int = 2                        # Размер отступа для вложенных операций
```

### Новые методы форматирования

```python
class OperationTableFormatter:
    def __init__(self, config: FormatterConfig = None):
        self.config = config or FormatterConfig()
        self._operation_counter = 0
    
    def format_operation_log(self, operation_log: OperationLog) -> str:
        """
        Форматирование лога операции с поддержкой метаопераций
        
        Args:
            operation_log: Лог операции для форматирования
            
        Returns:
            str: Форматированный текст лога
        """
        self._operation_counter += 1
        
        # Формирование заголовка
        header = self._format_operation_header(operation_log)
        
        # Выбор стратегии форматирования
        if (self.config.group_meta_operations and 
            operation_log.meta_operations):
            # Форматирование с группировкой
            table_content = self._format_with_meta_operations(operation_log)
        else:
            # Традиционное плоское форматирование
            table_content = self._format_flat_table(operation_log)
        
        # Формирование summary и footer
        summary = self._format_summary(operation_log)
        footer = self._format_operation_footer(operation_log)
        
        return f"{header}\n\n{table_content}\n\n{summary}\n{footer}\n{'=' * 80}"
```

### Форматирование с метаоперациями

```python
def _format_with_meta_operations(self, operation_log: OperationLog) -> str:
    """Форматирование таблицы с группировкой метаопераций"""
    
    # Определение операций, входящих в метагруппы
    grouped_operations = set()
    for meta_op in operation_log.meta_operations:
        grouped_operations.update(op.step_number for op in meta_op.sub_operations)
    
    # Сбор данных для таблицы
    table_rows = []
    
    # Добавление метаопераций
    for meta_op in operation_log.meta_operations:
        table_rows.extend(self._format_meta_operation_rows(meta_op))
    
    # Добавление негруппированных операций
    for sub_op in operation_log.sub_operations:
        if sub_op.step_number not in grouped_operations:
            table_rows.append(self._format_single_operation_row(sub_op))
    
    # Сортировка по времени начала
    table_rows.sort(key=lambda row: row.get('start_time', 0))
    
    # Формирование финальной таблицы
    return self._build_table_from_rows(table_rows)

def _format_meta_operation_rows(self, meta_op: MetaOperation) -> List[Dict]:
    """Форматирование строк для одной метаоперации"""
    rows = []
    
    if self.config.compact_meta_view:
        # Компактное представление метаоперации
        rows.append(self._create_meta_operation_summary_row(meta_op))
        
        # Детали операций (опционально)
        if (self.config.show_individual_ops and 
            len(meta_op.sub_operations) <= self.config.max_operations_inline):
            
            for sub_op in meta_op.sub_operations:
                rows.append(self._create_indented_operation_row(sub_op))
    
    else:
        # Развернутое представление
        rows.append(self._create_meta_operation_header_row(meta_op))
        for sub_op in meta_op.sub_operations:
            rows.append(self._create_indented_operation_row(sub_op))
        rows.append(self._create_meta_operation_footer_row(meta_op))
    
    return rows
```

## Форматы вывода метаопераций

### Компактный формат

```
================================================================================
Operation "ADD_REACTION" – STARTED (id=3, 2025-06-16 10:15:30)

+--------+--------------------------------+-----------+--------------------+----------+-----------+
|   Step | Sub-operation                  | Target    | Result data type   |  Status  |   Time, s |
+========+================================+===========+====================+==========+===========+
|    ► 1 | Time cluster: 3 ops in 45ms   | mixed     | mixed              |    OK    |     0.045 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      4 | OperationType.SAVE_DATA        | file_data | bool               |    OK    |     0.002 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|    ► 5 | Target 'series_data' batch     | series_d. | mixed              |    OK    |     0.025 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 8, successful 8, with errors 0, meta-operations 2, total time 0.072 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

### Развернутый формат

```
================================================================================
Operation "ADD_REACTION" – STARTED (id=3, 2025-06-16 10:15:30)

+--------+--------------------------------+-----------+--------------------+----------+-----------+
|   Step | Sub-operation                  | Target    | Result data type   |  Status  |   Time, s |
+========+================================+===========+====================+==========+===========+
|    ► 1 | ◣ Time cluster: 3 ops in 45ms | mixed     | mixed              |    OK    |     0.045 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      ├ | GET_VALUE                      | file_data | DataFrame          |    OK    |     0.015 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      ├ | SET_VALUE                      | file_data | bool               |    OK    |     0.012 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      └ | UPDATE_VALUE                   | file_data | bool               |    OK    |     0.018 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      4 | SAVE_DATA                      | file_data | bool               |    OK    |     0.002 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|    ► 5 | ◣ Target 'series_data' batch   | series_d. | mixed              |    OK    |     0.025 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      ├ | GET_SERIES_VALUE               | series_d. | dict               |    OK    |     0.008 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+
|      └ | UPDATE_SERIES                  | series_d. | bool               |    OK    |     0.017 |
+--------+--------------------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 8, successful 8, with errors 0, meta-operations 2, total time 0.072 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

### JSON формат для отладки

```python
def _format_debug_json(self, operation_log: OperationLog) -> str:
    """Формирование JSON представления для отладки"""
    
    debug_data = {
        "operation_name": operation_log.operation_name,
        "execution_time": operation_log.execution_time,
        "status": operation_log.status,
        
        "meta_operations": [
            {
                "meta_id": meta_op.meta_id,
                "strategy": meta_op.strategy_name,
                "description": meta_op.description,
                "operations_count": meta_op.operations_count,
                "duration_ms": meta_op.duration_ms,
                "success_count": meta_op.success_count,
                "error_count": meta_op.error_count,
                "operations": [
                    {
                        "step": op.step_number,
                        "name": op.operation_name,
                        "target": op.target,
                        "status": op.status,
                        "time": op.execution_time
                    }
                    for op in meta_op.sub_operations
                ]
            }
            for meta_op in operation_log.meta_operations
        ],
        
        "ungrouped_operations": [
            {
                "step": op.step_number,
                "name": op.operation_name,
                "target": op.target,
                "status": op.status,
                "time": op.execution_time
            }
            for op in operation_log.sub_operations
            if not any(op in meta_op.sub_operations for meta_op in operation_log.meta_operations)
        ]
    }
    
    return json.dumps(debug_data, indent=2, ensure_ascii=False)
```

## Реализация строк таблицы

### Создание строки метаоперации

```python
def _create_meta_operation_summary_row(self, meta_op: MetaOperation) -> Dict:
    """Создание суммарной строки метаоперации"""
    
    # Определение первого шага в группе
    first_step = min(op.step_number for op in meta_op.sub_operations)
    
    # Агрегация данных
    targets = list(set(op.target for op in meta_op.sub_operations))
    data_types = list(set(op.response_data_type for op in meta_op.sub_operations))
    statuses = list(set(op.status for op in meta_op.sub_operations))
    
    # Формирование сводной информации
    target_summary = targets[0] if len(targets) == 1 else "mixed"
    data_type_summary = data_types[0] if len(data_types) == 1 else "mixed"
    status_summary = statuses[0] if len(statuses) == 1 else "mixed"
    
    # Символ метаоперации
    symbol = self.config.meta_operation_symbol
    
    return {
        "step": f"{symbol} {first_step}",
        "sub_operation": meta_op.description,
        "target": target_summary[:10] + "." if len(target_summary) > 10 else target_summary,
        "result_data_type": data_type_summary,
        "status": status_summary,
        "time": f"{meta_op.total_execution_time:.3f}" if meta_op.total_execution_time else "0.000",
        "start_time": meta_op.start_time or 0
    }

def _create_indented_operation_row(self, sub_op: SubOperationLog) -> Dict:
    """Создание строки отдельной операции с отступом"""
    
    indent = " " * self.config.indent_size
    
    return {
        "step": f"{indent}├" if sub_op != sub_op else f"{indent}└",  # Логика ветвления
        "sub_operation": sub_op.operation_name,
        "target": sub_op.target,
        "result_data_type": sub_op.response_data_type,
        "status": sub_op.status,
        "time": f"{sub_op.execution_time:.3f}" if sub_op.execution_time else "0.000",
        "start_time": sub_op.start_time
    }
```

### Построение финальной таблицы

```python
def _build_table_from_rows(self, table_rows: List[Dict]) -> str:
    """Построение табличного представления из строк"""
    
    if not table_rows:
        return "No operations recorded."
    
    # Подготовка данных для tabulate
    headers = ["Step", "Sub-operation", "Target", "Result data type", "Status", "Time, s"]
    
    table_data = []
    for row in table_rows:
        table_data.append([
            row["step"],
            row["sub_operation"],
            row["target"], 
            row["result_data_type"],
            row["status"],
            row["time"]
        ])
    
    # Форматирование таблицы
    return tabulate(
        table_data,
        headers=headers,
        tablefmt=self.config.table_format,
        maxcolwidths=[8, self.config.max_cell_width, 10, 20, 10, 11]
    )
```

## Настройки форматирования в конфигурации

### Расширение конфигурационного файла

```python
# В src/core/logger_config.py

META_OPERATION_CONFIG = {
    "enabled": True,
    "debug_mode": False,
    
    # ...existing strategies config...
    
    # Настройки форматирования
    "formatting": {
        "group_meta_operations": True,      # Включить группировку в выводе
        "compact_meta_view": True,          # Компактное отображение
        "show_individual_ops": False,       # Показывать операции внутри групп
        "max_operations_inline": 5,         # Максимум операций inline
        "meta_operation_symbol": "►",       # Символ метаоперации
        "indent_size": 2,                   # Размер отступа
        
        # Дополнительные опции
        "show_meta_statistics": True,       # Показывать статистику групп
        "highlight_errors": True,           # Выделять ошибки в группах
        "time_precision": 3,                # Точность времени (знаков после запятой)
        
        # Режимы вывода
        "output_modes": {
            "default": "compact",           # Режим по умолчанию
            "debug": "expanded",            # Режим для отладки
            "json": False                   # Дополнительный JSON вывод
        }
    },
    
    # Фильтры отображения
    "display_filters": {
        "min_group_size": 2,                # Минимальный размер группы для отображения
        "max_group_size": 50,               # Максимальный размер для развернутого отображения
        "hide_successful_groups": False,    # Скрывать полностью успешные группы
        "hide_single_operations": False     # Скрывать одиночные операции
    }
}
```

### Динамическое переключение режимов

```python
class OperationTableFormatter:
    def set_output_mode(self, mode: str) -> None:
        """Динамическое изменение режима вывода"""
        
        mode_configs = {
            "compact": {
                "compact_meta_view": True,
                "show_individual_ops": False,
                "meta_operation_symbol": "►"
            },
            "expanded": {
                "compact_meta_view": False,
                "show_individual_ops": True,
                "meta_operation_symbol": "◣"
            },
            "debug": {
                "compact_meta_view": False,
                "show_individual_ops": True,
                "show_meta_statistics": True
            }
        }
        
        if mode in mode_configs:
            for key, value in mode_configs[mode].items():
                setattr(self.config, key, value)
```

## Обновление Summary блока

### Расширенная статистика

```python
def _format_summary(self, operation_log: OperationLog) -> str:
    """Форматирование блока summary с учётом метаопераций"""
    
    total_steps = len(operation_log.sub_operations)
    successful_steps = operation_log.successful_sub_operations_count
    error_steps = operation_log.failed_sub_operations_count
    total_time = operation_log.execution_time or 0
    
    base_summary = (
        f"SUMMARY: steps {total_steps}, successful {successful_steps}, "
        f"with errors {error_steps}"
    )
    
    # Добавление статистики метаопераций
    if operation_log.meta_operations:
        meta_count = len(operation_log.meta_operations)
        grouped_ops = sum(len(mo.sub_operations) for mo in operation_log.meta_operations)
        ungrouped_ops = total_steps - grouped_ops
        
        grouping_percentage = (grouped_ops / total_steps * 100) if total_steps > 0 else 0
        
        meta_summary = (
            f", meta-operations {meta_count}, "
            f"grouped {grouped_ops}/{total_steps} ops ({grouping_percentage:.1f}%)"
        )
        
        base_summary += meta_summary
    
    base_summary += f", total time {total_time:.3f} s."
    
    return base_summary
```

## Следующий этап

**Этап 6**: Интеграция, тестирование и документация - финальная интеграция всех компонентов, создание тестов и обновление документации.
