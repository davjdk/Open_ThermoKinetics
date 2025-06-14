# Этап 6: Автоматическое применение декораторов

## Цель этапа
Реализовать механизм автоматического применения декоратора `@operation` ко всем методам, соответствующим операциям из `OperationType`, исключив необходимость ручной маркировки.

## Задачи этапа

### 6.1 Анализ текущей структуры OperationType
- Изучить существующий перечень операций в `app_settings.OperationType`
- Определить соответствие операций и методов их обработки
- Выявить классы, содержащие методы-обработчики операций
- Создать карту связей операция → метод → класс

### 6.2 Проектирование механизма автодекорирования
- Выбрать подход: метакласс, декоратор класса или __init_subclass__
- Обеспечить сохранение сигнатур и метаданных методов
- Предусмотреть исключения для методов, не требующих логирования
- Спроектировать систему конфигурации автодекорирования

### 6.3 Реализация автоматического декорирования
- Создать механизм поиска методов по именам операций
- Реализовать безопасное применение декораторов
- Обеспечить совместимость с PyQt слотами и сигналами
- Добавить валидацию корректности применения

## Подходы к реализации

### 6.4 Вариант 1: Метакласс для автодекорирования
```python
class OperationAutoDecoratorMeta(type):
    """Метакласс для автоматического применения декораторов операций"""
    
    def __new__(mcs, name, bases, class_dict):
        # Получить список операций из OperationType
        operations = [op.value for op in OperationType]
        
        # Найти методы, соответствующие операциям
        for attr_name, attr_value in class_dict.items():
            if (callable(attr_value) and 
                attr_name.upper() in operations and
                not hasattr(attr_value, '_operation_decorated')):
                
                # Применить декоратор @operation
                class_dict[attr_name] = operation(attr_value)
                class_dict[attr_name]._operation_decorated = True
                
        return super().__new__(mcs, name, bases, class_dict)
        
class BaseOperationHandler(metaclass=OperationAutoDecoratorMeta):
    """Базовый класс для обработчиков операций с автодекорированием"""
    pass
```

### 6.5 Вариант 2: Декоратор класса
```python
def auto_decorate_operations(cls):
    """Декоратор класса для автоматического применения @operation"""
    
    operations = [op.value for op in OperationType]
    
    for attr_name in dir(cls):
        if (attr_name.upper() in operations and
            callable(getattr(cls, attr_name)) and
            not attr_name.startswith('_')):
            
            method = getattr(cls, attr_name)
            if not hasattr(method, '_operation_decorated'):
                decorated_method = operation(method)
                decorated_method._operation_decorated = True
                setattr(cls, attr_name, decorated_method)
    
    return cls

@auto_decorate_operations
class CalculationDataOperations:
    def add_reaction(self, *args, **kwargs):
        # Автоматически будет обёрнут декоратором @operation
        pass
```

### 6.6 Вариант 3: __init_subclass__ хук
```python
class OperationHandlerBase:
    """Базовый класс с автоматическим декорированием операций"""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._auto_decorate_operations()
    
    @classmethod
    def _auto_decorate_operations(cls):
        """Автоматически декорировать методы операций"""
        
        # Получить карту операций из конфигурации
        operation_mapping = get_operation_method_mapping()
        
        for operation_type, method_names in operation_mapping.items():
            for method_name in method_names:
                if hasattr(cls, method_name):
                    method = getattr(cls, method_name)
                    if (callable(method) and 
                        not hasattr(method, '_operation_decorated')):
                        
                        decorated = operation(operation_type=operation_type)(method)
                        decorated._operation_decorated = True
                        setattr(cls, method_name, decorated)
```

## Конфигурация автодекорирования

### 6.7 Карта операций и методов
```python
# В app_settings.py
OPERATION_METHOD_MAPPING = {
    OperationType.ADD_REACTION: ['add_reaction', 'create_reaction'],
    OperationType.REMOVE_REACTION: ['remove_reaction', 'delete_reaction'],
    OperationType.DECONVOLUTION: ['deconvolution', 'run_deconvolution'],
    OperationType.LOAD_FILE: ['load_file', 'import_file'],
    OperationType.MODEL_FIT_CALCULATION: ['model_fit_calculation'],
    OperationType.MODEL_FREE_CALCULATION: ['model_free_calculation'],
    # ... другие операции
}

# Исключения из автодекорирования
AUTO_DECORATION_EXCLUSIONS = [
    'private_method',
    'helper_function',
    '__init__',
    '__del__',
]

# Настройки автодекорирования
AUTO_DECORATION_CONFIG = {
    "enabled": True,                           # Включить автодекорирование
    "strict_matching": True,                   # Строгое соответствие имён
    "preserve_pyqt_slots": True,               # Сохранять PyQt слоты
    "log_decorating_process": False,           # Логировать процесс декорирования
    "validate_decorations": True,              # Проверять корректность применения
}
```

### 6.8 Система валидации автодекорирования
```python
class AutoDecorationValidator:
    """Валидатор корректности автоматического декорирования"""
    
    @staticmethod
    def validate_decorated_class(cls) -> List[str]:
        """
        Проверить корректность декорирования класса
        
        Returns:
            Список предупреждений/ошибок
        """
        warnings = []
        
        # Проверить, что все операции имеют соответствующие методы
        for operation in OperationType:
            expected_methods = OPERATION_METHOD_MAPPING.get(operation, [])
            for method_name in expected_methods:
                if hasattr(cls, method_name):
                    method = getattr(cls, method_name)
                    if not hasattr(method, '_operation_decorated'):
                        warnings.append(
                            f"Method {method_name} for {operation} not decorated"
                        )
        
        # Проверить PyQt совместимость
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if (hasattr(attr, '_operation_decorated') and 
                hasattr(attr, '__pyqtSignature__')):
                # Проверить сохранение PyQt метаданных
                pass
                
        return warnings
    
    @staticmethod
    def report_decoration_summary(cls):
        """Вывести сводку по декорированию класса"""
        decorated_methods = []
        
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_operation_decorated'):
                decorated_methods.append(attr_name)
        
        print(f"Auto-decorated methods in {cls.__name__}: {decorated_methods}")
```

## Интеграция с существующими классами

### 6.9 Применение к CalculationDataOperations
```python
# В src/core/calculation_data_operations.py
class CalculationDataOperations(OperationHandlerBase, BaseSlots):
    """
    Класс будет автоматически декорирован при определении
    Все методы, соответствующие OperationType, получат декоратор @operation
    """
    
    def add_reaction(self, file_name: str, **kwargs):
        # Автоматически декорирован как @operation(OperationType.ADD_REACTION)
        pass
    
    def remove_reaction(self, file_name: str, reaction_name: str):
        # Автоматически декорирован как @operation(OperationType.REMOVE_REACTION)
        pass
    
    def deconvolution(self, file_name: str, **params):
        # Автоматически декорирован как @operation(OperationType.DECONVOLUTION)
        pass
```

### 6.10 Применение к другим классам операций
```python
# Аналогично для других классов с операциями
class FileOperations(OperationHandlerBase):
    def load_file(self, file_path: str):
        # Автоматически декорирован
        pass

class SeriesOperations(OperationHandlerBase):
    def add_new_series(self, series_name: str):
        # Автоматически декорирован
        pass
```

## Обработка особых случаев

### 6.11 Сохранение PyQt метаданных
```python
def operation_preserving_pyqt(operation_type=None):
    """Декоратор операции с сохранением PyQt метаданных"""
    
    def decorator(func):
        # Сохранить PyQt атрибуты
        pyqt_signature = getattr(func, '__pyqtSignature__', None)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Логика декоратора @operation
            pass
        
        # Восстановить PyQt атрибуты
        if pyqt_signature:
            wrapper.__pyqtSignature__ = pyqt_signature
            
        wrapper._operation_decorated = True
        return wrapper
    
    return decorator
```

### 6.12 Обработка методов с нестандартными именами
```python
# Для методов, не следующих стандартному соглашению имён
class CustomOperationHandler(OperationHandlerBase):
    
    @operation(OperationType.SPECIAL_OPERATION)
    def non_standard_method_name(self):
        # Явное декорирование для нестандартных имён
        pass
    
    def _configure_auto_decoration(self):
        # Дополнительная конфигурация автодекорирования
        self._operation_method_overrides = {
            'special_method': OperationType.CUSTOM_OPERATION
        }
```

## Ожидаемые результаты
- Автоматическое применение декоратора `@operation` ко всем методам операций
- Сохранение совместимости с PyQt сигналами и слотами
- Система валидации корректности автодекорирования
- Конфигурируемые правила применения декораторов

## Критерии готовности
- Все методы из `OperationType` автоматически декорированы
- Сохранена функциональность PyQt компонентов
- Система валидации подтверждает корректность декорирования
- Нет необходимости в ручном применении декораторов

## Тестирование
- Тест автодекорирования различных классов операций
- Тест сохранения PyQt сигналов и слотов
- Тест валидации и отчётности по декорированию
- Тест производительности автодекорирования
- Тест обратной совместимости с существующим кодом

## Миграция
- Постепенный переход классов на автодекорирование
- Удаление ручных применений декоратора `@operation`
- Обновление документации по созданию новых операций
- Валидация миграции через автоматические тесты
