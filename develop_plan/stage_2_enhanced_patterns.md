# Этап 2: Расширенная детекция паттернов

**Место в общем плане:** Второй этап из 5. Расширение детекции паттернов с метаданными для подготовки к табличному форматированию.

## Цель этапа
Расширить PatternDetector для поддержки сложных паттернов с метаданными, которые будут использоваться в TabularFormatter на следующем этапе.

## Обновляемые файлы

### PatternDetector (pattern_detector.py)
- Добавление класса PatternGroup с метаданными
- Расширенные типы паттернов:
  - `plot_lines_addition` - добавление линий на график
  - `cascade_component_initialization` - каскадная инициализация  
  - `request_response_cycle` - циклы запрос-ответ
  - `file_operations` - файловые операции
  - `gui_updates` - обновления GUI

### AggregationEngine (aggregation_engine.py)  
- Обновление для работы с PatternGroup
- Создание AggregatedLogRecord с метаданными паттернов
- Улучшенная статистика по типам паттернов

### Config (config.py)
- Добавление параметров для управления расширенными паттернами
- Настройки приоритетов паттернов
- Конфигурация временных окон для разных типов

## Новая функциональность

### PatternGroup dataclass
```python
@dataclass
class PatternGroup:
    pattern_type: str
    records: List[LogRecord]
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any] = None
    
    @property
    def duration(self) -> timedelta
    @property  
    def count(self) -> int
```

### Расширенные методы детекции
- `_group_by_enhanced_patterns()` - группировка по расширенным типам
- `_get_enhanced_pattern_key()` - определение типа паттерна
- `_generate_pattern_metadata()` - генерация метаданных для каждого типа
- `_extract_plot_lines_metadata()` - метаданные для линий графика
- `_extract_file_operations_metadata()` - метаданные файловых операций
- `_extract_request_response_metadata()` - метаданные циклов запрос-ответ

### Каскадные паттерны
- `_process_cascade_pattern()` - обработка каскадных последовательностей
- `_detect_cascade_sequences()` - детекция каскадов инициализации
- `_generate_cascade_metadata()` - метаданные каскадных операций

## Обновление тестов

### test_pattern_detector.py
- Тесты для новых типов паттернов
- Проверка генерации метаданных
- Тесты каскадных паттернов
- Валидация PatternGroup структур

### test_aggregation_engine.py
- Тесты работы с PatternGroup
- Проверка метаданных в AggregatedLogRecord
- Статистика по типам паттернов

## Примеры использования

### Детекция паттерна добавления линий
```python
# Входные логи (реальные данные):
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F1/3' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/4' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3' to the plot.

# Результат:
PatternGroup(
    pattern_type="plot_lines_addition",
    metadata={
        'line_names': ['F1/3', 'F3/4', 'F3/2', 'F2', 'F3'],
        'table_suitable': True,
        'avg_line_time': 200.0,
        'unique_lines': 5
    }
)
```

### Детекция каскадной инициализации
```python 
# Входные логи (реальные данные):
2025-06-12 12:53:25 - INFO - user_guide_tab.py:25 - Initializing UserGuideTab
2025-06-12 12:53:25 - INFO - guide_framework.py:45 - Initializing GuideFramework
2025-06-12 12:53:25 - INFO - content_manager.py:46 - Initializing ContentManager
2025-06-12 12:53:25 - INFO - navigation_manager.py:88 - Initializing NavigationManager
2025-06-12 12:53:25 - INFO - renderer_manager.py:38 - Initializing RendererManager

# Результат:
PatternGroup(
    pattern_type="cascade_component_initialization", 
    metadata={
        'components': ['UserGuideTab', 'GuideFramework', 'ContentManager', 'NavigationManager', 'RendererManager'],
        'table_suitable': True,
        'initialization_order': ['UserGuideTab', 'GuideFramework', 'ContentManager', 'NavigationManager', 'RendererManager'],
        'cascade_depth': 5
    }
)
```

## Критерии готовности этапа
- [ ] PatternGroup класс создан и работает с метаданными
- [ ] Все 5 новых типов паттернов детектируются корректно
- [ ] Метаданные генерируются для каждого типа паттерна
- [ ] Каскадные паттерны обрабатываются правильно
- [ ] AggregationEngine работает с новыми PatternGroup
- [ ] Тесты покрывают новую функциональность (>85%)
- [ ] Обратная совместимость с этапом 1 сохранена
- [ ] Производительность остается приемлемой

## Подготовка к этапу 3
- Метаданные содержат флаг `table_suitable` для табличного форматирования
- Структуры данных готовы для TabularFormatter
- Типы паттернов стандартизированы для таблиц

## Следующий этап
Этап 3: TabularFormatter - создание табличного представления для агрегированных паттернов с метаданными.
