# Этап 5: Интеграция с TabularFormatter и вывод операций

## Цель этапа
Интегрировать созданный `OperationTableBuilder` с существующим `TabularFormatter` и обеспечить корректный вывод операционных таблиц в лог-файлы.

## Компоненты для модификации

### 5.1. TabularFormatter - поддержка операционных таблиц
Расширить `src/log_aggregator/tabular_formatter.py`:

#### Добавление нового типа таблиц:
```python
class TabularFormatter:
    def __init__(self):
        # Существующие типы...
        self.pattern_formatters.update({
            "operation_summary": self._format_operation_table,
        })
    
    def _format_operation_table(self, table_data: OperationTableData) -> str:
        """Форматировать таблицу операции"""
        
        # Создать заголовок операции
        title = self._create_operation_title(table_data.title, table_data.metadata)
        
        # Создать ASCII таблицу
        table = self._create_ascii_table(
            headers=table_data.headers,
            rows=table_data.rows,
            title=table_data.title
        )
        
        # Добавить итоговую строку
        summary = self._create_operation_summary(table_data.summary, table_data.metadata)
        
        # Объединить все части
        return f"{title}\n{table}\n{summary}\n"
    
    def _create_operation_title(self, title: str, metadata: Dict[str, Any]) -> str:
        """Создать заголовок для операции"""
        duration = metadata.get("total_duration")
        status = metadata.get("status", "UNKNOWN")
        
        title_line = f"{'=' * 80}"
        main_title = f"📋 {title}"
        
        if duration:
            duration_str = f"Время выполнения: {duration:.3f}s"
            main_title += f" ({duration_str})"
        
        return f"{title_line}\n{main_title}\n{title_line}"
```

### 5.2. Специализированное форматирование операций

#### Адаптивная ширина столбцов для операций:
```python
def _calculate_operation_column_widths(self, headers: List[str], rows: List[List[str]]) -> List[int]:
    """Рассчитать ширину столбцов для операционных таблиц"""
    
    # Базовые минимальные ширины для операционных столбцов
    min_widths = {
        "Sub-Operation": 20,
        "Start Time": 12,
        "Duration (s)": 12, 
        "Component": 15,
        "Status": 8,
        "Requests": 8,
        "MSE": 10,
        "R²": 8,
        "Files": 6,
        "Reactions": 9
    }
    
    # Рассчитать ширину на основе содержимого
    widths = []
    for i, header in enumerate(headers):
        # Минимальная ширина для данного столбца
        min_width = min_widths.get(header, 10)
        
        # Максимальная ширина содержимого
        content_widths = [len(header)]
        for row in rows:
            if i < len(row):
                content_widths.append(len(str(row[i])))
        
        # Итоговая ширина
        width = max(min_width, max(content_widths) + 2)
        widths.append(min(width, 25))  # Максимум 25 символов
    
    return widths

def _create_ascii_table(self, headers: List[str], rows: List[List[str]], title: str) -> str:
    """Создать ASCII таблицу для операции"""
    
    if not headers or not rows:
        return "Нет данных для отображения"
    
    # Рассчитать ширину столбцов
    widths = self._calculate_operation_column_widths(headers, rows)
    
    # Создать разделительную линию
    separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    # Создать заголовок таблицы
    header_row = "|" + "|".join(f" {h:{w}} " for h, w in zip(headers, widths)) + "|"
    
    # Создать строки данных
    data_rows = []
    for row in rows:
        # Дополнить строку пустыми значениями если нужно
        padded_row = row + [""] * (len(headers) - len(row))
        formatted_row = "|" + "|".join(f" {cell:{w}} " for cell, w in zip(padded_row, widths)) + "|"
        data_rows.append(formatted_row)
    
    # Объединить все части таблицы
    table_parts = [
        separator,
        header_row,
        separator
    ]
    table_parts.extend(data_rows)
    table_parts.append(separator)
    
    return "\n".join(table_parts)
```

### 5.3. Интеграция с AggregatingHandler

#### Отправка операционных таблиц через handler:
```python
class AggregatingHandler:
    def _send_operation_table(self, table_data: OperationTableData) -> None:
        """Отправить таблицу операции в лог"""
        
        # Создать BufferedLogRecord для операции
        operation_record = BufferedLogRecord(
            name="operation_aggregation",
            level=logging.INFO,
            pathname="operation_table",
            lineno=0,
            msg=f"Operation completed: {table_data.metadata.get('operation_name', 'UNKNOWN')}",
            args=(),
            exc_info=None
        )
        
        # Добавить метаданные операции
        operation_record.table_data = table_data
        operation_record.pattern_type = "operation_summary"
        operation_record.operation_name = table_data.metadata.get('operation_name')
        operation_record.operation_duration = table_data.metadata.get('total_duration')
        operation_record.operation_status = table_data.metadata.get('status')
        
        # Форматировать и отправить
        formatted_table = self.tabular_formatter.format_pattern(
            pattern_type="operation_summary",
            data=table_data
        )
        
        # Отправить в целевой handler
        final_record = logging.LogRecord(
            name="solid_state_kinetics.operations",
            level=logging.INFO,
            pathname="aggregated_operations",
            lineno=0,
            msg=formatted_table,
            args=(),
            exc_info=None
        )
        
        self.target_handler.emit(final_record)
```

### 5.4. Конфигурация вывода операций

#### Настройки для операционных таблиц:
```python
@dataclass 
class OperationFormattingConfig:
    """Конфигурация форматирования операций"""
    
    # Общие настройки
    enabled: bool = True
    show_sub_operations: bool = True
    show_metadata: bool = True
    max_table_width: int = 120
    
    # Настройки столбцов
    show_timestamps: bool = True
    show_duration: bool = True
    show_component: bool = True
    show_status_icons: bool = True
    
    # Настройки метрик
    show_request_count: bool = True
    show_custom_metrics: bool = True
    precision_seconds: int = 3
    precision_metrics: int = 6
    
    # Фильтрация
    min_operation_duration: float = 0.001  # Не показывать операции короче 1ms
    exclude_operations: List[str] = field(default_factory=list)
    
    # Группировка
    group_similar_operations: bool = False
    max_operations_per_group: int = 10

def apply_formatting_config(self, config: OperationFormattingConfig) -> None:
    """Применить конфигурацию форматирования"""
    self.config = config
    
    # Обновить форматтеры столбцов
    if not config.show_timestamps:
        self._remove_time_columns()
    
    if not config.show_custom_metrics:
        self._filter_custom_metric_columns()
```

### 5.5. Специализированные форматтеры операций

#### Форматтер для научных расчетов:
```python
def _format_scientific_operation(self, table_data: OperationTableData) -> str:
    """Специальный форматтер для научных операций"""
    
    operation_name = table_data.metadata.get('operation_name', '')
    
    if operation_name in ['DECONVOLUTION', 'MODEL_FIT_CALCULATION', 'MODEL_FREE_CALCULATION']:
        return self._format_calculation_operation(table_data)
    elif operation_name == 'ADD_NEW_SERIES':
        return self._format_data_operation(table_data)
    else:
        return self._format_operation_table(table_data)

def _format_calculation_operation(self, table_data: OperationTableData) -> str:
    """Форматтер для вычислительных операций"""
    
    # Добавить специфичную информацию для расчетов
    title_parts = [table_data.title]
    
    metadata = table_data.metadata
    if 'reactions_found' in metadata:
        title_parts.append(f"Реакций найдено: {metadata['reactions_found']}")
    
    if 'final_mse' in metadata:
        title_parts.append(f"Финальная MSE: {metadata['final_mse']:.6f}")
    
    enhanced_title = " | ".join(title_parts)
    
    # Создать таблицу с выделением научных метрик
    table = self._create_ascii_table(
        headers=table_data.headers,
        rows=table_data.rows,
        title=enhanced_title
    )
    
    return f"{self._create_operation_title(enhanced_title, metadata)}\n{table}\n{table_data.summary}\n"
```

### 5.6. Интеграция с логированием приложения

#### Автоматическая отправка операций в лог:
```python
# В OperationAggregator
def _finalize_operation(self, operation_group: OperationGroup, operation_metrics: OperationMetrics) -> None:
    """Завершить операцию и отправить в лог"""
    
    # Построить таблицу
    table_builder = OperationTableBuilder()
    table_data = table_builder.build_operation_table(operation_group, operation_metrics)
    
    # Отправить через AggregatingHandler
    if hasattr(self, 'aggregating_handler'):
        self.aggregating_handler._send_operation_table(table_data)
    
    # Логировать в debug режиме
    logger.debug(f"Operation {operation_metrics.operation_name} completed in {operation_metrics.duration:.3f}s")
    
    # Сохранить статистику
    self._update_operation_statistics(operation_metrics)

def _update_operation_statistics(self, metrics: OperationMetrics) -> None:
    """Обновить статистику операций"""
    if not hasattr(self, 'operation_stats'):
        self.operation_stats = defaultdict(list)
    
    self.operation_stats[metrics.operation_name].append({
        'duration': metrics.duration,
        'status': metrics.status,
        'request_count': metrics.request_count,
        'timestamp': time.time()
    })
```

### 5.7. Вывод в различные форматы

#### Поддержка множественных форматов вывода:
```python
class OperationOutputManager:
    """Менеджер вывода операций в различные форматы"""
    
    def __init__(self):
        self.formatters = {
            'ascii_table': TabularFormatter(),
            'json': JsonOperationFormatter(),
            'csv': CsvOperationFormatter()
        }
    
    def output_operation(self, table_data: OperationTableData, formats: List[str] = ['ascii_table']) -> None:
        """Вывести операцию в указанные форматы"""
        
        for format_name in formats:
            if format_name in self.formatters:
                formatter = self.formatters[format_name]
                output = formatter.format_operation(table_data)
                self._write_output(output, format_name, table_data.metadata.get('operation_name'))

def _write_output(self, content: str, format_name: str, operation_name: str) -> None:
    """Записать вывод в соответствующий файл"""
    
    if format_name == 'ascii_table':
        # В основной агрегированный лог
        logger.info(content)
    elif format_name == 'json':
        # В JSON файл для машинной обработки
        self._write_to_json_log(content, operation_name)
    elif format_name == 'csv':
        # В CSV для анализа в Excel/Python
        self._write_to_csv_log(content, operation_name)
```

## Примеры выходных данных

### Пример таблицы ADD_NEW_SERIES:
```
================================================================================
📋 ✅ Операция: Добавление серии данных (Время выполнения: 1.254s)
================================================================================
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
| Sub-Operation        | Time     | Duration (s) | Component       | Status | Files | Heat Rates       |
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
| GET_ALL_DATA         | 14:23:45 | 0.145        | file_data       | ✅     | 3     | 3, 5, 10         |
| Data Processing      | 14:23:45 | 0.089        | main_window     | ✅     | 3     | 3, 5, 10         |
| Plot Update          | 14:23:45 | 0.234        | plot_canvas     | ✅     | 3     | 3, 5, 10         |
| ADD_NEW_SERIES       | 14:23:45 | 0.567        | series_data     | ✅     | 3     | 3, 5, 10         |
| GET_SERIES           | 14:23:46 | 0.098        | series_data     | ✅     | 3     | 3, 5, 10         |
| UI Update            | 14:23:46 | 0.121        | main_window     | ✅     | 3     | 3, 5, 10         |
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
Итог: ✅ | Время: 1.254s | Запросов: 3 | Файлов: 3 | Скорости: 3, 5, 10 K/min
```

### Пример таблицы DECONVOLUTION:
```
================================================================================
📋 🔬 Операция: Деконволюция пиков (Время выполнения: 5.678s)
================================================================================
+----------------------+----------+--------------+-----------+--------+----------+----------+--------+
| Sub-Operation        | Time     | Duration (s) | Component | Status | Реакции  | MSE      | R²     |
+----------------------+----------+--------------+-----------+--------+----------+----------+--------+
| Peak Deconvolution   | 14:25:12 | 5.678        | Calcs     | ✅     | 3        | 0.000245 | 0.9987 |
+----------------------+----------+--------------+-----------+--------+----------+----------+--------+
Итог: ✅ | Время: 5.678s | Запросов: 1 | Реакций: 3 | MSE: 0.000245
```

## Критерии завершения этапа
1. ✅ Интегрирован `OperationTableBuilder` с `TabularFormatter`
2. ✅ Добавлена поддержка нового типа таблиц "operation_summary"
3. ✅ Реализовано специализированное форматирование для операций
4. ✅ Создана система автоматической отправки таблиц в лог
5. ✅ Добавлена конфигурация форматирования операций
6. ✅ Реализованы специализированные форматтеры для научных расчетов
7. ✅ Написаны unit-тесты для интеграции
8. ✅ Проверен вывод таблиц в агрегированный лог

## Ожидаемый результат
После завершения этапа система будет автоматически генерировать и выводить в лог структурированные таблицы для каждой завершенной операции, обеспечивая детальное отслеживание выполнения пользовательских действий в удобочитаемом формате.
