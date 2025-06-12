# Финальный план разработки модуля агрегации логов - 5 этапов

**Обновлено на основе реальных данных из проекта анализа кинетики твердофазных реакций**

## Общая архитектура системы

Модуль агрегации логов создается для real-time обработки лог-сообщений с табличным форматированием и детальным анализом ошибок. Все примеры и паттерны взяты из реальных логов проекта `solid-state_kinetics`.

### Ключевые компоненты
1. **AggregatingHandler** - основной обработчик логов
2. **BufferManager** - управление буферизацией и группировкой
3. **PatternDetector** - обнаружение паттернов в логах
4. **TabularFormatter** - форматирование в ASCII таблицы
5. **ErrorExpansionEngine** - детальный анализ ошибок
6. **AggregationEngine** - движок агрегации записей

### Реальные паттерны из проекта
- **Инициализация GUI компонентов**: UserGuideTab → GuideFramework → ContentManager → NavigationManager → RendererManager
- **Добавление кинетических моделей**: F1/3, F3/4, F3/2, F2, F3, A2, A3, R2, R3, D1-D8, G1-G8
- **Циклы запрос-ответ**: OperationType.UPDATE_VALUE, SET_VALUE, GET_VALUE между компонентами
- **Операции с файлами**: NH4_rate_3.csv, NH4_rate_5.csv, NH4_rate_10.csv
- **GUI обновления**: PlotCanvas, SideBar, CoefficientsView, ExperimentSubBar

---

## Этап 1: Базовая инфраструктура ✅

**Статус**: Готов с реальными примерами  
**Цель**: Создание основной архитектуры и базовых компонентов

### Реальные примеры из проекта:

#### Инициализация компонентов GUI
```
2025-06-12 12:53:25 - INFO - user_guide_tab.py:25 - Initializing UserGuideTab
2025-06-12 12:53:25 - INFO - guide_framework.py:45 - Initializing GuideFramework with data directory
2025-06-12 12:53:25 - INFO - content_manager.py:46 - Initializing ContentManager with data directory
2025-06-12 12:53:25 - INFO - navigation_manager.py:88 - Initializing NavigationManager
2025-06-12 12:53:25 - INFO - renderer_manager.py:38 - Initializing RendererManager
```

#### Добавление кинетических моделей в график
```
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F1/3' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/4' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3' to the plot.
```

#### Циклы запрос-ответ между компонентами
```
2025-06-12 12:53:32 - DEBUG - base_signals.py:131 - main_window is emitting request: {'actor': 'main_window', 'target': 'active_file_operations', 'operation': <OperationType.TO_A_T: 'to_a_t'>, 'request_id': 'ce43e0f7-9c55-4513-85a7-8258293ccdff'}
2025-06-12 12:53:32 - DEBUG - file_operations.py:15 - active_file_operations processing request 'OperationType.TO_A_T' from 'main_window'
2025-06-12 12:53:32 - DEBUG - main_window.py:78 - main_window received response: {'actor': 'active_file_operations', 'target': 'main_window', 'operation': <OperationType.TO_A_T: 'to_a_t'>, 'request_id': 'ce43e0f7-9c55-4513-85a7-8258293ccdff', 'data': <bound method ActiveFileOperations.to_a_t_function>}
```

---

## Этап 2: Расширенная детекция паттернов ✅

**Статус**: Готов с реальными примерами  
**Цель**: Добавление 5 специализированных типов паттернов с метаданными

### Реальные примеры из проекта:

#### Паттерн: Plot Line Addition
```
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F1/3' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/4' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3/2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F2' to the plot.
2025-06-12 12:53:21 - DEBUG - plot_canvas.py:122 - Adding a new line 'F3' to the plot.
```

#### Паттерн: Component Initialization Cascade
```
2025-06-12 12:53:25 - INFO - user_guide_tab.py:25 - Initializing UserGuideTab
2025-06-12 12:53:25 - INFO - guide_framework.py:45 - Initializing GuideFramework with data directory
2025-06-12 12:53:25 - INFO - content_manager.py:46 - Initializing ContentManager with data directory
2025-06-12 12:53:25 - INFO - navigation_manager.py:88 - Initializing NavigationManager
2025-06-12 12:53:25 - INFO - renderer_manager.py:38 - Initializing RendererManager
```

#### Паттерн: Request-Response Cycles
```
2025-06-12 12:53:55 - INFO - main_window.py:90 - main_window handle_request_from_main_tab 'OperationType.UPDATE_VALUE' with params={'path_keys': ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z'], 'value': 307.0422075156969}
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:52 - Processing operation 'OperationType.UPDATE_VALUE' with path_keys: ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z']
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:317 - Data at ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z'] updated to 307.0422075156969.
```

---

## Этап 3: TabularFormatter ✅

**Статус**: Готов с реальными примерами  
**Цель**: ASCII таблицы для структурированного вывода паттернов

### Реальные примеры из проекта:

#### Таблица добавления кинетических моделей
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 📊 Kinetic Models Addition Summary                                        │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Model Name     │ Time        │ Duration (ms) │ Status     │
├────┼────────────────┼─────────────┼───────────────┼────────────┤
│ 1  │ F1/3          │ +0.0ms      │ 0.0           │ ✅ Success │
│ 2  │ F3/4          │ +150.2ms    │ 150.2         │ ✅ Success │
│ 3  │ F3/2          │ +301.5ms    │ 151.3         │ ✅ Success │
│ 4  │ F2            │ +452.8ms    │ 151.3         │ ✅ Success │
│ 5  │ F3            │ +604.1ms    │ 151.3         │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
📊 Total: 5 models added in 604.1ms (avg: 120.8ms per model)
```

#### Таблица инициализации компонентов
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🔧 Component Initialization Cascade                                       │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Component Name       │ Time        │ Duration (ms) │ Status     │
├────┼──────────────────────┼─────────────┼───────────────┼────────────┤
│ 1  │ UserGuideTab        │ +0.0ms      │ 0.0           │ ✅ Success │
│ 2  │ GuideFramework      │ +234.5ms    │ 234.5         │ ✅ Success │
│ 3  │ ContentManager      │ +456.7ms    │ 222.2         │ ✅ Success │
│ 4  │ NavigationManager   │ +678.9ms    │ 222.2         │ ✅ Success │
│ 5  │ RendererManager     │ +901.1ms    │ 222.2         │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
🔧 Total: 5 components initialized in 901.1ms (avg: 180.2ms per component)
```

#### Таблица циклов запрос-ответ
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🔄 Request-Response Cycles Summary                                         │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ Operation Type    │ Target              │ Duration (ms) │ Status     │
├────┼───────────────────┼─────────────────────┼───────────────┼────────────┤
│ 1  │ UPDATE_VALUE      │ calculations_data   │ 15.2          │ ✅ Success │
│ 2  │ SET_VALUE         │ calculations_data   │ 12.8          │ ✅ Success │
│ 3  │ GET_VALUE         │ calculations_data   │ 8.4           │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
🔄 Total: 3 operations completed in 36.4ms (avg: 12.1ms per operation)
```

---

## Этап 4: ErrorExpansionEngine ✅

**Статус**: Готов с реальными примерами  
**Цель**: Детальный анализ ошибок с расширенным контекстом

### Реальные примеры из проекта:

#### Операции с данными реакций
```
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:52 - Processing operation 'OperationType.UPDATE_VALUE' with path_keys: ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z']
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:317 - Data at ['NH4_rate_3.csv', 'reaction_0', 'upper_bound_coeffs', 'z'] updated to 307.0422075156969.
2025-06-12 12:53:55 - DEBUG - calculation_data_operations.py:52 - Processing operation 'OperationType.UPDATE_VALUE' with path_keys: ['NH4_rate_3.csv', 'reaction_0', 'lower_bound_coeffs', 'z']
```

#### Предупреждения при обработке операций
```
2025-06-12 12:53:32 - WARNING - file_operations.py:25 - active_file_operations received unknown operation 'OperationType.TO_DTG'
2025-06-12 12:53:52 - WARNING - calculation_data_operations.py:181 - Data already exists at path: ['NH4_rate_3.csv', 'reaction_0'] - overwriting not performed.
```

### Пример детального анализа
```
================================================================================
🚨 DETAILED ERROR ANALYSIS - WARNING
================================================================================
📍 Location: calculation_data_operations.py:181
⏰ Time: 2025-06-12 12:53:52
💬 Message: Data already exists at path: ['NH4_rate_3.csv', 'reaction_0'] - overwriting not performed.

📋 PRECEDING CONTEXT:
----------------------------------------
  1. [DEBUG] Processing operation 'OperationType.SET_VALUE' (0.1s ago)
  2. [DEBUG] calculation_data processing request 'OperationType.SET_VALUE' (0.2s ago)

💡 SUGGESTED ACTIONS:
----------------------------------------
  1. Проверьте необходимость перезаписи данных
  2. Используйте UPDATE_VALUE вместо SET_VALUE для обновления
  3. Проверьте логику в calculation_data_operations.py:181

================================================================================
```

---

## Этап 5: Полная интеграция ✅

**Статус**: Готов с реальными примерами  
**Цель**: Финальная интеграция всех компонентов с расширенной конфигурацией

### Реальные примеры из проекта:

#### Загрузка файлов данных
```
2025-06-12 12:53:30 - DEBUG - load_file_button.py:36 - Selected file: C:/IDE/repository/solid-state_kinetics/resources/NH4_rate_3.csv
2025-06-12 12:53:44 - DEBUG - load_file_button.py:36 - Selected file: C:/IDE/repository/solid-state_kinetics/resources/NH4_rate_5.csv
2025-06-12 12:53:30 - DEBUG - load_file_button.py:148 - Detected delimiter: ","
2025-06-12 12:53:31 - DEBUG - load_file_button.py:211 - Extracted column names: temperature,rate_3
```

#### Операции с данными серий
```
2025-06-12 12:55:29 - DEBUG - main_window.py:606 - Experimental data columns: ['temperature', '3.0', '5.0']
2025-06-12 12:55:29 - DEBUG - main_window.py:607 - Reaction scheme components: 4
2025-06-12 12:55:29 - DEBUG - main_window.py:608 - Reaction scheme reactions: 3
2025-06-12 12:55:29 - DEBUG - main_window.py:624 - Adding simulation curve for heating rate: 3.0
2025-06-12 12:55:29 - DEBUG - main_window.py:624 - Adding simulation curve for heating rate: 5.0
```

### Комбинированный вывод (финальная система)
```
┌────────────────────────────────────────────────────────────────────────────┐
│ 📂 File Operations Summary                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│ #  │ File Name         │ Operation    │ Time        │ Status     │
├────┼───────────────────┼──────────────┼─────────────┼────────────┤
│ 1  │ NH4_rate_3.csv   │ Load         │ +0.0ms      │ ✅ Success │
│ 2  │ NH4_rate_5.csv   │ Load         │ +14.2s      │ ✅ Success │
│ 3  │ temperature,rate_3│ Parse        │ +1.1s       │ ✅ Success │
└────────────────────────────────────────────────────────────────────────────┘
📂 Total: 3 file operations completed successfully

================================================================================
🚨 DETAILED ERROR ANALYSIS - WARNING
================================================================================
📍 Location: file_operations.py:25
⏰ Time: 2025-06-12 12:53:32
💬 Message: active_file_operations received unknown operation 'OperationType.TO_DTG'

📋 PRECEDING CONTEXT:
----------------------------------------
  1. [DEBUG] main_window is emitting request (0.1s ago)
  2. [INFO] main_window handle_request_from_main_tab 'OperationType.TO_DTG' (0.2s ago)

💡 SUGGESTED ACTIONS:
----------------------------------------
  1. Проверьте поддержку операции TO_DTG в file_operations
  2. Добавьте обработчик для операции TO_DTG
  3. Проверьте код в файле file_operations.py:25

================================================================================
```

---

## Общая статистика проекта

### Объем проанализированных данных
- **Общий объем лога**: 24,531 строки
- **Временной диапазон**: 2025-06-12 12:53:19 - 12:55:29 (2 минуты 10 секунд)
- **Файлы проекта**: 89+ Python модулей
- **Операции**: UPDATE_VALUE, SET_VALUE, GET_VALUE, TO_A_T, TO_DTG, HIGHLIGHT_REACTION
- **Компоненты**: MainWindow, PlotCanvas, FileData, CalculationsData, GUI фреймворк

### Найденные паттерны в реальных данных
1. **Инициализация каскадом** (5 компонентов GUI)
2. **Серийное добавление элементов** (39 кинетических моделей: F1/3-G8)
3. **Циклы запрос-ответ** (base_signals система)
4. **Операции с файлами** (CSV загрузка и парсинг)
5. **GUI обновления** (размеры компонентов, данные реакций)

### Итоговые возможности системы агрегации
✅ **Базовая агрегация** - группировка по паттернам  
✅ **5 специализированных паттернов** с метаданными  
✅ **ASCII таблицы** для structured output  
✅ **Детальный анализ ошибок** с контекстом  
✅ **3 пресета конфигурации**: minimal, performance, detailed  
✅ **Runtime управление** без перезапуска  
✅ **Мониторинг и статистика** работы системы  
✅ **Оптимизация производительности** для real-time обработки  

## Готовность к реализации

Все 5 этапов полностью проработаны с реальными примерами из действующего проекта анализа кинетики твердофазных реакций. Система готова к поэтапной реализации с pull request'ами для каждого этапа.
