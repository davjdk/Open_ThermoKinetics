# Этап 3: TabularFormatter - табличное представление данных

**Место в общем плане:** Третий этап из 5. Добавление TabularFormatter для структурированного вывода агрегированных паттернов в виде таблиц.

## Цель этапа
Создать TabularFormatter для автоматического преобразования агрегированных паттернов в удобочитаемые ASCII таблицы с адаптивным форматированием.

## Создаваемые файлы

### TabularFormatter (tabular_formatter.py)
- Основной класс для табличного форматирования
- TableData dataclass для представления табличных данных
- Специализированные методы для каждого типа паттерна
- ASCII форматирование с адаптивной шириной колонок

### Обновление конфигурации (config.py)
```python
@dataclass
class TabularFormattingConfig:
    enabled: bool = True
    max_table_width: int = 120
    max_rows_per_table: int = 20
    ascii_tables: bool = True
    include_summaries: bool = True
    auto_format_patterns: List[str] = None
```

## Новая функциональность

### TableData структура
```python
@dataclass
class TableData:
    title: str
    headers: List[str]
    rows: List[List[str]]
    summary: Optional[str] = None
    table_type: str = 'generic'
```

### Специализированные таблицы по типам паттернов

#### 1. Plot Lines Addition Table
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 📊 Plot Lines Addition Summary                                            │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Line Name      │ Time        │ Duration (ms) │ Status     │
├────┼────────────────┼─────────────┼───────────────┼────────────┤
│ 1  │ F1/3           │ +0.0ms      │ 0.0           │ ✅ Success │
│ 2  │ F3/4           │ +50.2ms     │ 50.2          │ ✅ Success │
│ 3  │ F3/2           │ +100.5ms    │ 100.5         │ ✅ Success │
│ 4  │ F2             │ +150.8ms    │ 150.8         │ ✅ Success │
│ 5  │ F3             │ +201.1ms    │ 201.1         │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
📊 Total: 5 kinetic model lines added in 201.1ms (avg: 40.2ms per line)
```

#### 2. Component Initialization Cascade Table
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🔧 Component Initialization Cascade                                       │
├────────────────────────────────────────────────────────────────────────────┤
│ Step │ Component           │ Time        │ Duration (ms) │ Status │
├──────┼─────────────────────┼─────────────┼───────────────┼────────┤
│ 1    │ UserGuideTab        │ +0.0ms      │ 0.0           │ ✅ OK  │
│ 2    │ GuideFramework      │ +125.5ms    │ 125.5         │ ✅ OK  │
│ 3    │ ContentManager      │ +250.2ms    │ 124.7         │ ✅ OK  │
│ 4    │ NavigationManager   │ +375.8ms    │ 125.6         │ ✅ OK  │
│ 5    │ RendererManager     │ +501.3ms    │ 125.5         │ ✅ OK  │
└────────────────────────────────────────────────────────────────────────────┘
📊 Initialization cascade: 5 components in 501.3ms
```

#### 3. Request-Response Cycles Table
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🔄 Request-Response Cycles                                                │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Operation       │ Time         │ Duration (ms) │ Status     │
├────┼─────────────────┼──────────────┼───────────────┼────────────┤
│ 1  │ UPDATE_VALUE    │ 12:53:55.123 │ 15.2          │ ✅ Complete│
│ 2  │ SET_VALUE       │ 12:53:55.200 │ 8.7           │ ✅ Complete│
│ 3  │ GET_VALUE       │ 12:53:55.250 │ 12.1          │ ✅ Complete│
└────────────────────────────────────────────────────────────────────────────┘
📊 Request-Response cycles: 3 operations, avg: 12.0ms
```

#### 4. File Operations Table  
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 📁 File Operations Summary                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Operation │ File                │ Time         │ Status     │
├────┼───────────┼─────────────────────┼──────────────┼────────────┤
│ 1  │ Load      │ NH4_rate_3.csv      │ 12:53:30.000 │ ✅ Success │
│ 2  │ Load      │ NH4_rate_5.csv      │ 12:53:44.000 │ ✅ Success │
│ 3  │ Process   │ TO_A_T function     │ 12:53:47.850 │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
📊 File operations: load: 2, process: 1
```

#### 5. GUI Updates Table
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🖥️ GUI Updates Batch                                                       │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Component     │ Update Type │ Time        │ Duration (ms) │
├────┼───────────────┼─────────────┼─────────────┼───────────────┤
│ 1  │ PlotCanvas    │ AddLine     │ +0.0ms      │ 0.0           │
│ 2  │ SideBar       │ SetActive   │ +45.2ms     │ 45.2          │
│ 3  │ CoefficientsView│ Received   │ +102.8ms    │ 57.6          │
└────────────────────────────────────────────────────────────────────────────┘
📊 GUI updates: 3 operations in 102.8ms
```

## Ключевые методы

### Основные методы форматирования
- `format_patterns_as_tables()` - главный метод форматирования
- `_create_table_for_pattern()` - создание таблицы для паттерна
- `_format_ascii_table()` - ASCII форматирование
- `_calculate_column_widths()` - адаптивная ширина колонок

### Специализированные методы создания таблиц
- `_create_plot_lines_table()` - таблица линий графика
- `_create_initialization_table()` - таблица инициализации
- `_create_request_response_table()` - таблица запрос-ответ  
- `_create_file_operations_table()` - таблица файловых операций
- `_create_gui_updates_table()` - таблица обновлений GUI
- `_create_generic_table()` - универсальная таблица

### Вспомогательные методы извлечения данных
- `_extract_operation_type()` - тип операции
- `_extract_file_name()` - имя файла
- `_extract_gui_component()` - GUI компонент
- `_group_request_response_pairs()` - группировка в пары

## Интеграция с AggregatingHandler

### Обновление AggregatingHandler
```python
def _process_buffer(self) -> None:
    # Existing aggregation code...
    
    # Табличное форматирование (если включено)
    if self.enable_tabular_format and patterns:
        table_records = self.tabular_formatter.format_patterns_as_tables(patterns)
        aggregated_records.extend(table_records)
        self.stats['tables_generated'] += len(table_records)
```

### Новые методы управления
```python
def toggle_tabular_format(self, enabled: bool) -> None:
    """Включение/выключение табличного формата"""
    self.enable_tabular_format = enabled
```

## Тестирование

### test_tabular_formatter.py
- Тесты создания всех типов таблиц
- Проверка ASCII форматирования
- Тесты адаптивной ширины колонок
- Валидация TableData структур
- Тесты ограничений размера таблиц

### Интеграционные тесты
- Тесты интеграции с AggregatingHandler
- Проверка включения/выключения табличного режима
- Тесты производительности с большими таблицами

## Критерии готовности этапа
- [ ] TabularFormatter создан и работает со всеми типами паттернов
- [ ] Все 5 типов специализированных таблиц реализованы
- [ ] ASCII форматирование работает с адаптивной шириной
- [ ] Ограничения размера таблиц соблюдаются
- [ ] Интеграция с AggregatingHandler завершена
- [ ] Тесты покрывают функциональность (>85%)
- [ ] Производительность остается приемлемой
- [ ] Можно включать/выключать табличный режим в runtime

## Ограничения этапа
- Пока нет детального анализа ошибок
- Только ASCII таблицы (без HTML/богатого форматирования)
- Фиксированный набор типов таблиц

## Следующий этап
Этап 4: ErrorExpansionEngine - детальный анализ ошибок с контекстом и рекомендациями.
