# Этап 4.5: Агрегаторы операций и значений - оптимизация производительности логирования

**Место в общем плане:** Промежуточный этап между 4 и 5. Добавление OperationAggregator и ValueAggregator для радикального сокращения объема логов при сохранении критической информации.

## Цель этапа
Решить две критические проблемы производительности логирования:
1. **Каскадные операции**: Агрегировать цепочки из 10-15 системных операций в единые сводные записи
2. **Объемные значения**: Сворачивать массивы NumPy, pandas DataFrames и коэффициенты с раскрытием при ошибках

## Анализ проблем из логов solid-state-kinetics

### Проблема 1: Операционные каскады
```
2025-06-13 00:11:51 - INFO - main_window.py:90 - handle_request_from_main_tab 'ADD_REACTION'
2025-06-13 00:11:51 - DEBUG - base_signals.py:131 - emitting request: ADD_REACTION
2025-06-13 00:11:51 - DEBUG - calculation_data_operations.py:52 - Processing operation 'ADD_REACTION'
2025-06-13 00:11:51 - DEBUG - base_signals.py:131 - emitting request: CHECK_OPERATION
2025-06-13 00:11:51 - DEBUG - file_data.py:221 - processing request 'CHECK_OPERATION'
2025-06-13 00:11:51 - DEBUG - base_signals.py:131 - emitting request: GET_DF_DATA
...еще 10 строк системных вызовов
```

### Проблема 2: Объемные значения  
```
'x': array([ 32.18783,  33.14274,  34.09766, ... 486 элементов ... 498.18635])
'data': DataFrame([489 rows x 2 columns])
'coeffs': {'h': 0.005452850632157724, 'z': 265.18708750511246, 'w': 46.599852, ...}
```

## Создаваемые файлы

### OperationAggregator (operation_aggregator.py)
- OperationGroup dataclass для группировки операций
- Детекция корневых операций (инициаторов каскадов)
- Группировка по временным окнам (1 секунда)
- Агрегирование системных вызовов в сводные записи

### ValueAggregator (value_aggregator.py)  
- ValueSummary dataclass для краткого описания значений
- Сворачивание NumPy arrays, pandas DataFrames, словарей коэффициентов
- Кэширование полных значений для раскрытия при ошибках
- Настраиваемые пороги агрегации

### Обновление конфигурации (config.py)
```python
@dataclass
class OperationAggregationConfig:
    enabled: bool = True
    cascade_window: float = 1.0  # секунды
    min_cascade_size: int = 3
    root_operations: Set[str] = field(default_factory=lambda: {
        'ADD_REACTION', 'REMOVE_REACTION', 'MODEL_BASED_CALCULATION',
        'DECONVOLUTION', 'MODEL_FIT_CALCULATION', 'MODEL_FREE_CALCULATION',
        'LOAD_FILE', 'TO_DTG', 'SMOOTH_DATA', 'SUBTRACT_BACKGROUND'
    })

@dataclass  
class ValueAggregationConfig:
    enabled: bool = True
    array_threshold: int = 10
    dataframe_threshold: int = 5
    dict_threshold: int = 8
    string_threshold: int = 200
    cache_size_limit: int = 100
```

## Новая функциональность

### OperationGroup структура
```python
@dataclass
class OperationGroup:
    """Группа связанных операций"""
    root_operation: str  # ADD_REACTION, MODEL_BASED_CALCULATION, etc.
    start_time: datetime
    end_time: datetime
    operation_count: int
    actors: Set[str] = field(default_factory=set)
    operations: List[str] = field(default_factory=list)
    request_ids: Set[str] = field(default_factory=set)
    has_errors: bool = False
    has_warnings: bool = False
```

### ValueSummary структура
```python
@dataclass 
class ValueSummary:
    """Краткое описание значения"""
    original_length: int
    data_type: str
    shape: Optional[Tuple[int, ...]]
    preview: str
    full_content: str  # Сохраняем для детального вывода при ошибках
```

### Паттерны детекции операций
```python
self.operation_patterns = [
    re.compile(r"handle_request_from_main_tab '(\w+)'"),
    re.compile(r"processing request '(\w+)'"),
    re.compile(r"emitting request.*'operation': <OperationType\.(\w+)"),
    re.compile(r"OPERATION (START|END): (\w+)")
]
```

### Паттерны детекции значений
```python
self.patterns = {
    'numpy_array': re.compile(r'array\(\[([\d\.,\s\-e]+)\]\)'),
    'dataframe': re.compile(r'(temperature|rate_\d+).*?\[(\d+) rows x (\d+) columns\]'),
    'coeffs_dict': re.compile(r"'coeffs': \{([^}]+)\}"),
    'bounds_dict': re.compile(r"'(upper_bound_coeffs|lower_bound_coeffs)': \{([^}]+)\}"),
    'request_dict': re.compile(r"emitting request: (\{.+\})")
}
```

## Алгоритмы агрегации

### Операционная агрегация
1. **Детекция корневой операции**: Поиск операций-инициаторов (ADD_REACTION, DECONVOLUTION)
2. **Группировка каскада**: Сбор последующих операций в окне 1 секунда
3. **Анализ статуса**: Проверка наличия ошибок/предупреждений в группе
4. **Генерация сводки**: Создание единой записи с метриками

### Агрегация значений
1. **Анализ типа данных**: Определение NumPy array, DataFrame, dict
2. **Проверка размера**: Сравнение с настроенными порогами
3. **Создание превью**: Генерация краткого описания с примерами
4. **Кэширование**: Сохранение полных значений для контекста ошибок

## Результаты агрегации

### Пример операционной агрегации
**До (15 строк)**:
```
2025-06-13 00:11:51 - INFO - main_window.py:90 - handle_request_from_main_tab 'ADD_REACTION'
2025-06-13 00:11:51 - DEBUG - base_signals.py:131 - emitting request: ADD_REACTION
...13 строк системных вызовов...
```

**После (1 строка)**:
```
2025-06-13 00:11:51 - INFO - operation_aggregator.py:0 - 🔄 OPERATION CASCADE: ADD_REACTION | ⏱️ 0.05s | 📊 15 operations | 🎭 Actors: base_signals, calculation_data_operations, main_window, plot_canvas
```

### Пример агрегации значений
**До**:
```
'x': array([ 32.18783,  33.14274,  34.09766,  35.05257, ... 485 элементов ... 498.18635])
```

**После**:
```
'x': 📊 array(489 elements) [32.18783, 33.14274, 34.09766, ..., 497.23143, 498.18635]
```

## Интеграция с AggregatingHandler

### Новые параметры инициализации
```python
def __init__(self, 
             target_handler: logging.Handler,
             # ... существующие параметры ...
             enable_operation_aggregation: bool = True,
             enable_value_aggregation: bool = True,
             cascade_window: float = 1.0,
             min_cascade_size: int = 3):
```

### Обновленный emit метод
```python
def emit(self, record: logging.LogRecord) -> None:
    """Обработка с новыми агрегаторами"""
    if not self.enabled:
        self.target_handler.emit(record)
        return
    
    try:
        with self._lock:
            log_record = self._convert_record(record)
            
            # НОВОЕ: Агрегация значений (всегда, кроме ошибок)
            if (self.enable_value_aggregation and 
                not self._is_error_record(log_record)):
                log_record.message = self.value_aggregator.process_message(log_record)
            
            # НОВОЕ: Обработка операционных каскадов
            if self.enable_operation_aggregation:
                completed_group = self.operation_aggregator.process_record(log_record)
                if completed_group:
                    # Отправляем агрегированную запись
                    aggregated_record = self.operation_aggregator.get_aggregated_record(completed_group)
                    self.target_handler.emit(aggregated_record.raw_record or 
                                           self._create_log_record(aggregated_record))
                    self.stats['operation_cascades_aggregated'] += 1
                    return
            
            # Обработка ошибок с восстановлением полных значений
            if self._is_error_record(log_record):
                if self.enable_value_aggregation:
                    full_context = self.value_aggregator.get_full_context(log_record)
                    if full_context:
                        log_record.message = full_context
                
                if self.enable_error_expansion:
                    self._handle_error_immediately(log_record)
                    return
            
            # Стандартная обработка
            # ... остальной код ...
```

### Методы управления агрегаторами
```python
def toggle_operation_aggregation(self, enabled: bool) -> None:
    """Включение/выключение агрегации операций"""
    self.enable_operation_aggregation = enabled

def toggle_value_aggregation(self, enabled: bool) -> None:
    """Включение/выключение агрегации значений"""
    self.enable_value_aggregation = enabled

def get_aggregation_stats(self) -> Dict[str, Any]:
    """Статистика агрегаторов"""
    stats = {}
    
    if self.enable_operation_aggregation:
        stats.update({
            'operation_cascades_aggregated': self.stats.get('operation_cascades_aggregated', 0),
            'current_cascade_size': self.operation_aggregator.current_group.operation_count 
                                  if self.operation_aggregator.current_group else 0
        })
    
    if self.enable_value_aggregation:
        stats.update(self.value_aggregator.get_stats())
    
    return stats
```

## Специальная обработка ошибок

### Восстановление контекста при ошибках
```python
def _handle_error_with_full_context(self, record: LogRecord) -> None:
    """Обработка ошибки с восстановлением полных значений"""
    # Восстанавливаем несвернутые значения
    if self.enable_value_aggregation:
        full_context = self.value_aggregator.get_full_context(record)
        if full_context:
            record.message = full_context
    
    # Применяем стандартное расширение ошибки
    if self.enable_error_expansion:
        expanded_record = self.error_expansion_engine.expand_error(
            record, 
            self.buffer_manager.get_recent_context()
        )
        self.target_handler.emit(expanded_record)
    else:
        self.target_handler.emit(record.raw_record)
```

## Производительность и метрики

### Ожидаемые улучшения
- **Сокращение объема логов операций**: 85-90%
- **Сокращение объема логов значений**: 80-85%
- **Общее сокращение объема логов**: 80-90%
- **Сохранение критической информации**: 100% при ошибках

### Метрики производительности
```python
{
    'operation_cascades_aggregated': 45,
    'values_compressed': 1230,
    'cache_hits_on_errors': 12,
    'compression_ratio_operations': 0.89,
    'compression_ratio_values': 0.83,
    'current_cascade_size': 7,
    'cached_values': 87
}
```

## Тестирование

### test_operation_aggregator.py
- Тесты детекции корневых операций
- Проверка группировки каскадов по времени
- Тесты агрегации с ошибками и предупреждениями
- Валидация OperationGroup структур
- Тесты производительности при высокой нагрузке

### test_value_aggregator.py
- Тесты сворачивания NumPy arrays разных размеров
- Проверка агрегации pandas DataFrames
- Тесты обработки словарей коэффициентов
- Валидация кэширования для контекста ошибок
- Тесты паттернов детекции типов данных

### test_integration_aggregators.py
- Интеграционные тесты с AggregatingHandler
- Тесты совместной работы обоих агрегаторов
- Проверка восстановления контекста при ошибках
- Тесты включения/выключения агрегаторов в runtime
- Тесты производительности под нагрузкой

### Примеры тестовых сценариев
```python
def test_operation_cascade_aggregation(self):
    """Тест агрегации операционного каскада"""
    # Создаем серию операций ADD_REACTION
    base_time = datetime.now()
    
    # Корневая операция
    root_record = create_log_record(
        message="handle_request_from_main_tab 'ADD_REACTION'",
        timestamp=base_time
    )
    
    # Системные операции в каскаде
    system_records = [
        create_log_record(f"emitting request: operation_{i}", base_time + timedelta(milliseconds=i*10))
        for i in range(1, 15)
    ]
    
    # Обрабатываем операции
    completed_group = None
    for record in [root_record] + system_records:
        result = self.operation_aggregator.process_record(record)
        if result:
            completed_group = result
    
    # Проверяем агрегацию
    self.assertIsNotNone(completed_group)
    self.assertEqual(completed_group.root_operation, "ADD_REACTION")
    self.assertEqual(completed_group.operation_count, 15)
    self.assertLessEqual(
        (completed_group.end_time - completed_group.start_time).total_seconds(),
        1.0
    )

def test_value_aggregation_with_error_context(self):
    """Тест агрегации значений с восстановлением при ошибке"""
    # Создаем запись с большим массивом
    large_array_record = create_log_record(
        message="data: array([1.0, 2.0, 3.0, ..., 500 elements])"
    )
    
    # Агрегируем значение
    aggregated_message = self.value_aggregator.process_message(large_array_record)
    self.assertIn("📊 array(500 elements)", aggregated_message)
    
    # Создаем ошибку
    error_record = create_log_record(
        message="Processing failed",
        level="ERROR",
        timestamp=large_array_record.timestamp + timedelta(milliseconds=100)
    )
    
    # Восстанавливаем полный контекст
    full_context = self.value_aggregator.get_full_context(large_array_record)
    self.assertIsNotNone(full_context)
    self.assertIn("array([1.0, 2.0, 3.0, ..., 500 elements])", full_context)
```

## Критерии готовности этапа
- [ ] OperationAggregator создан и корректно группирует каскады
- [ ] ValueAggregator эффективно сворачивает все типы данных
- [ ] Агрегаторы интегрированы в AggregatingHandler
- [ ] Контекст ошибок полностью восстанавливается при WARNING/ERROR
- [ ] Настраиваемые пороги агрегации работают корректно
- [ ] Кэширование значений функционирует без утечек памяти
- [ ] Производительность улучшена на 80-90% по объему логов
- [ ] Тесты покрывают функциональность (>90%)
- [ ] Можно включать/выключать каждый агрегатор независимо
- [ ] Метрики агрегации отображаются в статистике

## Ограничения этапа
- Фиксированные паттерны детекции операций и значений
- Простая логика группировки по временным окнам
- Базовые алгоритмы сворачивания без машинного обучения
- Ограниченный размер кэша для контекста ошибок

## Влияние на существующие компоненты

### BufferManager
- Дополнительное отслеживание операционных групп
- Расширенная статистика агрегации

### PatternDetector  
- Интеграция с операционными паттернами
- Учет агрегированных операций при детекции

### AggregationEngine
- Обработка агрегированных операционных групп
- Специальная логика для сжатых значений

## Следующий этап
Этап 5: Полная интеграция и расширенная конфигурация - объединение всех компонентов включая новые агрегаторы с продвинутыми настройками, пресетами и комплексными сценариями использования.
