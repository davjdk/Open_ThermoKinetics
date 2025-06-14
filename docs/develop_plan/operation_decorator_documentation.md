# Enhanced @operation Decorator Documentation

## Обзор

Расширенный декоратор `@operation` представляет собой мощную систему автоматического логирования операций с интеграцией в существующую архитектуру `BaseSlots` и автоматическим определением типов операций из `OperationType` enum.

## Основные возможности

### ✅ Автоматическое определение типов операций
- Интеграция с `OperationType` enum (38 операций)  
- Автоматическое сопоставление имен методов с типами операций
- Поддержка паттернов именования (`_handle_`, `process_`, etc.)

### ✅ Интеграция с BaseSlots
- Автоматическое декорирование `process_request` методов
- Поддержка существующей сигнально-слотовой архитектуры
- Совместимость с PyQt декораторами (`@pyqtSlot`)

### ✅ Обработка исключений
- Настраиваемая обработка исключений (`handle_exceptions=True/False`)
- Автоматическое логирование деталей ошибок
- Сохранение или пропуск исключений

### ✅ Поддержка вложенных операций
- Thread-local стек операций
- Автоматическое обнаружение вложенных вызовов
- Корректное управление иерархией операций

### ✅ Сохранение метаданных
- Полное сохранение сигнатур и документации функций
- Совместимость с `functools.wraps`
- Возможность интроспекции декорированных методов

## Использование

### 1. Базовое использование

```python
from src.log_aggregator.operation_decorator import operation
from src.core.app_settings import OperationType

# Автоматическое определение типа операции
@operation
def add_reaction(self, reaction_data):
    # Автоматически определится как OperationType.ADD_REACTION
    pass

# Явное указание типа операции
@operation(OperationType.LOAD_FILE)
def load_file(self, file_path):
    pass

# Кастомное имя операции
@operation("CUSTOM_OPERATION")
def custom_method(self):
    pass
```

### 2. Автоматическое декорирование BaseSlots классов

```python
from src.log_aggregator.operation_metaclass import operation_aware_class

@operation_aware_class
class MyDataOperations(BaseSlots):
    def process_request(self, params):
        # Автоматически декорируется при определении класса
        operation = params.get("operation")
        # ... обработка операции
```

### 3. Использование метакласса

```python
from src.log_aggregator.operation_metaclass import AutoOperationMeta

class MyOperations(BaseSlots, metaclass=AutoOperationMeta):
    def process_request(self, params):
        # Автоматически декорируется метаклассом
        pass
```

### 4. Настройка обработки исключений

```python
# Исключения обрабатываются и логируются, метод возвращает None
@operation("SAFE_OPERATION", handle_exceptions=True)
def safe_method(self):
    raise ValueError("Error occurred")
    
# Исключения логируются и пропускаются дальше
@operation("UNSAFE_OPERATION", handle_exceptions=False)
def unsafe_method(self):
    raise ValueError("Error occurred")  # Будет поднято
```

## Автоматическое определение операций

Декоратор автоматически сопоставляет имена методов с `OperationType` enum:

### Точные совпадения
- `add_reaction` → `OperationType.ADD_REACTION`
- `deconvolution` → `OperationType.DECONVOLUTION`
- `load_file` → `OperationType.LOAD_FILE`

### Совпадения с префиксами
- `_handle_add_reaction` → `OperationType.ADD_REACTION`
- `handle_deconvolution` → `OperationType.DECONVOLUTION`
- `process_load_file` → `OperationType.LOAD_FILE`

### Паттерн-совпадения
- Методы содержащие `model_based` → `OperationType.MODEL_BASED_CALCULATION`
- Методы содержащие `model_fit` → `OperationType.MODEL_FIT_CALCULATION`
- Методы содержащие `model_free` → `OperationType.MODEL_FREE_CALCULATION`

## Интеграция с существующим кодом

### Обратная совместимость

Новый декоратор полностью совместим с существующим использованием:

```python
# Существующий код продолжает работать
from src.log_aggregator.operation_logger import operation

@operation("EXISTING_OPERATION")
def existing_method(self):
    pass
```

### Постепенная миграция

```python
# Этап 1: Добавить импорт нового декоратора
from src.log_aggregator.operation_decorator import operation as enhanced_operation

# Этап 2: Заменить декораторы постепенно
@enhanced_operation  # Вместо @operation
def my_method(self):
    pass

# Этап 3: Применить автоматическое декорирование к классам
@operation_aware_class
class MyClass(BaseSlots):
    pass
```

## Логирование и метрики

Декоратор автоматически собирает следующие метрики:

### Базовые метрики
- `function_name` - Имя декорированной функции
- `module_name` - Модуль, содержащий функцию  
- `is_nested` - Флаг вложенной операции
- `args_count` - Количество позиционных аргументов
- `kwargs_keys` - Ключи именованных аргументов

### Специальные параметры
- `param_operation` - Тип операции из параметров
- `param_path_keys` - Path keys для доступа к данным
- `param_file_name` - Имя файла из параметров
- `param_params` - Параметры операции

### Результаты выполнения
- `has_result` - Наличие результата выполнения
- `result_type` - Тип возвращаемого значения
- `exception_type` - Тип исключения (при ошибке)
- `exception_message` - Сообщение об ошибке

## Примеры логов

### Успешная операция
```
🔄 OPERATION_START: ADD_REACTION (ID: ADD_REACTION_20241214_143022_a1b2)
│ ├─ Метрика: function_name = add_reaction
│ ├─ Метрика: module_name = src.core.calculation_data_operations
│ ├─ Метрика: is_nested = False
│ ├─ Метрика: param_operation = add_reaction
│ ├─ Метрика: has_result = True
│ ├─ Метрика: result_type = dict
✅ OPERATION_END: ADD_REACTION (Время: 0.045s, Статус: SUCCESS)
```

### Операция с ошибкой
```
🔄 OPERATION_START: LOAD_FILE (ID: LOAD_FILE_20241214_143023_c3d4)
│ ├─ Метрика: function_name = load_file
│ ├─ Метрика: exception_type = FileNotFoundError
│ ├─ Метрика: exception_message = File not found: test.csv
❌ OPERATION_END: LOAD_FILE (Время: 0.002s, Статус: ERROR)
```

### Вложенные операции
```
🔄 OPERATION_START: COMPLEX_WORKFLOW (ID: COMPLEX_WORKFLOW_20241214_143024_e5f6)
│ 🔄 OPERATION_START: PREPROCESS_DATA (ID: PREPROCESS_DATA_20241214_143024_g7h8)
│ │ ├─ Метрика: is_nested = True
│ │ ✅ OPERATION_END: PREPROCESS_DATA (Время: 0.012s, Статус: SUCCESS)
│ 🔄 OPERATION_START: ANALYZE_DATA (ID: ANALYZE_DATA_20241214_143024_i9j0)
│ │ ├─ Метрика: is_nested = True
│ │ ✅ OPERATION_END: ANALYZE_DATA (Время: 0.028s, Статус: SUCCESS)
✅ OPERATION_END: COMPLEX_WORKFLOW (Время: 0.055s, Статус: SUCCESS)
```

## Конфигурация

### Параметры декоратора

```python
@operation(
    operation_type="CUSTOM_OP",    # Явный тип операции
    auto_detect=True,              # Автоопределение типа
    handle_exceptions=True,        # Обработка исключений  
    preserve_metadata=True         # Сохранение метаданных
)
def my_method(self):
    pass
```

### Глобальные настройки

```python
from src.log_aggregator.operation_logger import get_operation_logger

# Получение экземпляра логгера
op_logger = get_operation_logger()

# Настройка компрессии данных
op_logger.compression_config.enabled = True
op_logger.compression_config.array_threshold = 10
```

## API для программного использования

### Проверка активных операций

```python
from src.log_aggregator.operation_decorator import (
    get_current_operation_context,
    is_operation_active
)

# Получить имя текущей операции
current_op = get_current_operation_context()  # "ADD_REACTION" или None

# Проверить, активна ли операция
if is_operation_active():
    print("Операция выполняется")
```

### Ретроактивное декорирование

```python
from src.log_aggregator.operation_decorator import auto_decorate_baseslots_class

# Применить декорирование к существующему классу
auto_decorate_baseslots_class(MyExistingClass)
```

### Массовое применение

```python
from src.log_aggregator.operation_metaclass import apply_auto_decoration_to_existing_classes

# Применить ко всем существующим BaseSlots классам
apply_auto_decoration_to_existing_classes()
```

## Тестирование

### Проверка декорирования

```python
def test_method_is_decorated():
    @operation("TEST_OP")
    def test_func():
        pass
    
    assert hasattr(test_func, "_is_operation_decorated")
    assert test_func._operation_name == "TEST_OP"
```

### Мокирование в тестах

```python
from unittest.mock import patch

def test_operation_logging():
    with patch("src.log_aggregator.operation_decorator.get_operation_logger") as mock:
        mock_logger = Mock()
        mock.return_value = mock_logger
        
        @operation("TEST")
        def test_func():
            return "result"
            
        result = test_func()
        
        mock_logger.start_operation.assert_called_once_with("TEST")
        assert result == "result"
```

## Устранение неисправностей

### Декоратор не применяется
1. Проверьте наследование от `BaseSlots`
2. Убедитесь, что метод называется `process_request`
3. Проверьте корректность импортов

### Неправильное определение типа операции
1. Добавьте явный параметр `operation_type`
2. Проверьте соответствие имени метода паттернам
3. Используйте `OperationType` enum напрямую

### Проблемы с исключениями
1. Установите `handle_exceptions=False` для отладки
2. Проверьте логи для деталей ошибок
3. Используйте try/catch в самом методе

### Конфликты с PyQt
1. Убедитесь, что `preserve_metadata=True`
2. Применяйте `@operation` после `@pyqtSlot`
3. Тестируйте сигнально-слотовые соединения

## Планы развития

### Следующие этапы
1. **Этап 3**: Упрощение OperationLogger (удаление auto-mode)
2. **Этап 4**: Интеграция TabularFormatter для агрегированного вывода
3. **Этап 5**: Интерфейс обработки ошибок операций
4. **Этап 6**: Автоматическое применение ко всем 38 операциям

### Планируемые улучшения
- Поддержка асинхронных операций
- Интеграция с системой метрик производительности
- Расширенная конфигурация через файлы настроек
- Визуализация дерева операций в GUI

---

**Статус**: ✅ Этап 2 завершен - Создание нового декоратора @operation
**Следующий этап**: Этап 3 - Упрощение OperationLogger
