# Этап 4: Создание OperationTableBuilder для табличного представления

## Цель этапа
Создать компонент `OperationTableBuilder` для преобразования собранных метрик операций в структурированное табличное представление.

## Компоненты для создания

### 4.1. OperationTableBuilder - основной класс
Создать новый файл `src/log_aggregator/operation_table_builder.py`:

```python
@dataclass
class OperationTableData:
    """Данные для табличного представления операции"""
    title: str
    headers: List[str]
    rows: List[List[str]]
    summary: Optional[str] = None
    table_type: str = "operation_summary"
    metadata: Dict[str, Any] = field(default_factory=dict)

class OperationTableBuilder:
    """Построитель таблиц операций"""
    
    # Базовые столбцы таблицы операций
    BASE_COLUMNS = [
        "Sub-Operation",      # Название подоперации
        "Start Time",         # Время начала (ЧЧ:ММ:СС)
        "Duration (s)",       # Длительность в секундах
        "Component",          # Компонент, выполняющий операцию
        "Status"              # Статус (✅/⚠️/❌)
    ]
    
    # Дополнительные столбцы в зависимости от метрик
    OPTIONAL_COLUMNS = {
        "request_count": "Requests",
        "mse_value": "MSE",
        "r_squared": "R²", 
        "file_count": "Files",
        "reaction_count": "Reactions",
        "heating_rates": "Heat Rates",
        "cpu_usage_avg": "CPU %",
        "memory_usage_mb": "Memory MB"
    }
```

### 4.2. Генерация таблиц операций

#### Основной метод построения таблицы:
```python
def build_operation_table(self, 
                         operation_group: OperationGroup, 
                         operation_metrics: OperationMetrics) -> OperationTableData:
    """Построить таблицу для завершенной операции"""
    
    # Определить столбцы на основе доступных метрик
    headers = self._determine_columns(operation_metrics)
    
    # Сгенерировать строки для подопераций
    rows = self._generate_sub_operation_rows(operation_group, operation_metrics, headers)
    
    # Создать заголовок операции
    title = self._generate_operation_title(operation_metrics)
    
    # Создать итоговую строку
    summary = self._generate_operation_summary(operation_metrics)
    
    return OperationTableData(
        title=title,
        headers=headers,
        rows=rows,
        summary=summary,
        metadata={
            "operation_name": operation_metrics.operation_name,
            "total_duration": operation_metrics.duration,
            "status": operation_metrics.status
        }
    )

def _determine_columns(self, metrics: OperationMetrics) -> List[str]:
    """Определить столбцы таблицы на основе доступных метрик"""
    columns = self.BASE_COLUMNS.copy()
    
    # Добавить дополнительные столбцы если есть соответствующие метрики
    for metric_key, column_name in self.OPTIONAL_COLUMNS.items():
        if metric_key in metrics.custom_metrics:
            columns.append(column_name)
    
    return columns
```

### 4.3. Генерация строк подопераций

#### Анализ подопераций из лог-записей:
```python
def _generate_sub_operation_rows(self, 
                               operation_group: OperationGroup,
                               operation_metrics: OperationMetrics,
                               headers: List[str]) -> List[List[str]]:
    """Сгенерировать строки для подопераций"""
    
    sub_operations = self._extract_sub_operations(operation_group)
    rows = []
    
    for i, sub_op in enumerate(sub_operations):
        row = self._create_sub_operation_row(sub_op, headers, i == 0)
        rows.append(row)
    
    # Добавить итоговую строку операции
    if sub_operations:
        total_row = self._create_total_operation_row(operation_metrics, headers)
        rows.append(total_row)
    
    return rows

def _extract_sub_operations(self, operation_group: OperationGroup) -> List[SubOperation]:
    """Извлечь подоперации из группы логов"""
    sub_operations = []
    current_sub_op = None
    
    for record in operation_group.records:
        message = record.getMessage()
        
        # Обнаружить начало новой подоперации
        sub_op_name = self._detect_sub_operation_start(message)
        if sub_op_name:
            # Завершить предыдущую подоперацию
            if current_sub_op:
                current_sub_op.end_time = record.created
                sub_operations.append(current_sub_op)
            
            # Начать новую подоперацию
            current_sub_op = SubOperation(
                name=sub_op_name,
                start_time=record.created,
                component=self._extract_component(record),
                status="IN_PROGRESS"
            )
        
        # Добавить метрики к текущей подоперации
        if current_sub_op:
            self._add_metrics_to_sub_operation(current_sub_op, record)
    
    # Завершить последнюю подоперацию
    if current_sub_op:
        current_sub_op.end_time = operation_group.records[-1].created
        sub_operations.append(current_sub_op)
    
    return sub_operations
```

### 4.4. Специализированные таблицы для типов операций

#### Таблица для ADD_NEW_SERIES:
```python
def _build_add_series_table(self, operation_group: OperationGroup, 
                           operation_metrics: OperationMetrics) -> OperationTableData:
    """Специализированная таблица для операции ADD_NEW_SERIES"""
    
    # Специфичные подоперации для добавления серии
    expected_sub_ops = [
        "GET_ALL_DATA",           # Получение данных файлов
        "Data Processing",        # Обработка и объединение данных  
        "Plot Update",           # Обновление графика
        "ADD_NEW_SERIES",        # Добавление в систему
        "GET_SERIES",            # Получение схемы реакций
        "UI Update"              # Обновление интерфейса
    ]
    
    # Создать строки с ожидаемыми подоперациями
    rows = []
    for sub_op_name in expected_sub_ops:
        sub_op_data = self._find_sub_operation_data(operation_group, sub_op_name)
        if sub_op_data:
            row = [
                sub_op_name,
                self._format_time(sub_op_data.start_time),
                f"{sub_op_data.duration:.3f}",
                sub_op_data.component,
                self._format_status(sub_op_data.status)
            ]
            
            # Добавить специфичные метрики
            if sub_op_name == "Data Processing":
                file_count = operation_metrics.custom_metrics.get("file_count", "N/A")
                heating_rates = operation_metrics.custom_metrics.get("heating_rates", [])
                row.extend([str(file_count), ", ".join(map(str, heating_rates))])
            
            rows.append(row)
    
    return OperationTableData(
        title=f"🔄 Операция: Добавление серии данных",
        headers=["Подоперация", "Время", "Длительность", "Компонент", "Статус", "Файлы", "Скорости нагрева"],
        rows=rows,
        summary=self._generate_series_summary(operation_metrics)
    )
```

#### Таблица для DECONVOLUTION:
```python
def _build_deconvolution_table(self, operation_group: OperationGroup,
                              operation_metrics: OperationMetrics) -> OperationTableData:
    """Специализированная таблица для операции DECONVOLUTION"""
    
    rows = []
    
    # Основная подоперация деконволюции
    deconv_data = self._find_sub_operation_data(operation_group, "DECONVOLUTION")
    if deconv_data:
        row = [
            "Peak Deconvolution",
            self._format_time(deconv_data.start_time),
            f"{deconv_data.duration:.3f}",
            "Calculations",
            self._format_status(deconv_data.status)
        ]
        
        # Добавить метрики деконволюции
        reactions = operation_metrics.custom_metrics.get("reactions_found", "N/A")
        mse = operation_metrics.custom_metrics.get("final_mse", "N/A")
        r_squared = operation_metrics.custom_metrics.get("r_squared", "N/A")
        
        row.extend([str(reactions), f"{mse:.6f}" if isinstance(mse, (int, float)) else str(mse)])
        if isinstance(r_squared, (int, float)):
            row.append(f"{r_squared:.4f}")
        else:
            row.append(str(r_squared))
        
        rows.append(row)
    
    return OperationTableData(
        title=f"🔬 Операция: Деконволюция пиков",
        headers=["Подоперация", "Время", "Длительность", "Компонент", "Статус", "Реакции", "MSE", "R²"],
        rows=rows,
        summary=self._generate_deconvolution_summary(operation_metrics)
    )
```

### 4.5. Форматирование данных

#### Утилиты форматирования:
```python
def _format_time(self, timestamp: float) -> str:
    """Форматировать время в читаемый вид"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%H:%M:%S.%f")[:-3]  # ЧЧ:ММ:СС.ммм

def _format_duration(self, duration: float) -> str:
    """Форматировать длительность"""
    if duration < 0.001:
        return f"{duration*1000:.1f}ms"
    elif duration < 1.0:
        return f"{duration*1000:.0f}ms"
    else:
        return f"{duration:.3f}s"

def _format_status(self, status: str) -> str:
    """Форматировать статус с иконками"""
    status_icons = {
        "SUCCESS": "✅",
        "WARNING": "⚠️", 
        "ERROR": "❌",
        "IN_PROGRESS": "🔄",
        "TIMEOUT": "⏱️"
    }
    return status_icons.get(status, status)

def _format_metric_value(self, value: Any, metric_type: str) -> str:
    """Форматировать значение метрики"""
    if metric_type in ["mse_value", "r_squared"]:
        return f"{float(value):.6f}" if isinstance(value, (int, float)) else str(value)
    elif metric_type in ["cpu_usage_avg"]:
        return f"{float(value):.1f}%" if isinstance(value, (int, float)) else str(value)
    elif metric_type in ["duration"]:
        return self._format_duration(float(value)) if isinstance(value, (int, float)) else str(value)
    else:
        return str(value)
```

### 4.6. Генерация итоговых строк

#### Итоговые сводки для операций:
```python
def _generate_operation_summary(self, metrics: OperationMetrics) -> str:
    """Сгенерировать итоговую строку операции"""
    status_icon = self._format_status(metrics.status)
    duration = self._format_duration(metrics.duration) if metrics.duration else "N/A"
    
    summary_parts = [
        f"Итог: {status_icon}",
        f"Время: {duration}",
        f"Запросов: {metrics.request_count}"
    ]
    
    if metrics.warning_count > 0:
        summary_parts.append(f"Предупреждений: {metrics.warning_count}")
    
    if metrics.error_count > 0:
        summary_parts.append(f"Ошибок: {metrics.error_count}")
    
    # Добавить специфичные метрики
    if "file_count" in metrics.custom_metrics:
        summary_parts.append(f"Файлов: {metrics.custom_metrics['file_count']}")
    
    if "reactions_found" in metrics.custom_metrics:
        summary_parts.append(f"Реакций: {metrics.custom_metrics['reactions_found']}")
    
    return " | ".join(summary_parts)

def _generate_operation_title(self, metrics: OperationMetrics) -> str:
    """Сгенерировать заголовок операции"""
    status_icon = self._format_status(metrics.status)
    
    # Человекочитаемые названия операций
    operation_names = {
        "ADD_NEW_SERIES": "Добавление серии данных",
        "DECONVOLUTION": "Деконволюция пиков", 
        "MODEL_FIT_CALCULATION": "Model-Fit расчеты",
        "MODEL_FREE_CALCULATION": "Model-Free расчеты",
        "MODEL_BASED_CALCULATION": "Model-Based оптимизация",
        "LOAD_DECONVOLUTION_RESULTS": "Загрузка результатов деконволюции",
        "SELECT_SERIES": "Выбор серии"
    }
    
    operation_title = operation_names.get(metrics.operation_name, metrics.operation_name)
    return f"{status_icon} Операция: {operation_title}"
```

## Интеграция с существующими компонентами

### Связь с OperationAggregator:
```python
# В OperationAggregator.end_operation()
def end_operation(self) -> None:
    if self.current_group and self.current_group.explicit_mode:
        # Получить метрики от OperationMonitor
        operation_metrics = self.operation_monitor.end_operation_tracking()
        
        # Построить таблицу
        table_builder = OperationTableBuilder()
        table_data = table_builder.build_operation_table(self.current_group, operation_metrics)
        
        # Передать в TabularFormatter
        self._send_to_tabular_formatter(table_data)
        
        self._close_current_group()
```

## Критерии завершения этапа
1. ✅ Создан класс `OperationTableBuilder` с базовым функционалом
2. ✅ Реализована структура `OperationTableData` для данных таблиц
3. ✅ Добавлено извлечение подопераций из лог-записей
4. ✅ Созданы специализированные таблицы для основных типов операций
5. ✅ Реализовано форматирование данных и метрик
6. ✅ Добавлена генерация итоговых строк и заголовков
7. ✅ Написаны unit-тесты для компонента
8. ✅ Проверена интеграция с `OperationAggregator` и `OperationMonitor`

## Ожидаемый результат
После завершения этапа система сможет автоматически генерировать структурированные таблицы для завершенных операций, содержащие детальную информацию о подоперациях, метриках и статусе выполнения, готовые для форматирования через `TabularFormatter`.
