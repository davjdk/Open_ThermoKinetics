# Этап 5: Интерфейс обработки ошибок операций

## Цель этапа
Создать расширяемый интерфейс для обработки ошибок операций с возможностью подключения пользовательских обработчиков.

## Задачи этапа

### 5.1 Проектирование интерфейса OperationErrorHandler
- Определить абстрактный базовый класс или протокол
- Спроектировать методы для различных типов ошибок
- Обеспечить передачу полного контекста операции
- Предусмотреть возможность восстановления после ошибок

### 5.2 Интеграция с OperationLogger
- Добавить поддержку регистрации обработчиков ошибок
- Обеспечить автоматический вызов обработчика при ошибках
- Сохранить информацию об ошибке в метриках операции
- Поддержать цепочку обработчиков (chain of responsibility)

### 5.3 Реализация базового обработчика
- Создать стандартный обработчик для логирования ошибок
- Реализовать форматирование сообщений об ошибках
- Добавить опциональную отправку уведомлений
- Обеспечить совместимость с существующей системой логирования

## Интерфейс OperationErrorHandler

### Абстрактный базовый класс
```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class OperationErrorHandler(ABC):
    """Интерфейс для обработки ошибок операций"""
    
    @abstractmethod
    def handle_operation_error(
        self, 
        error: Exception, 
        operation_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обработать ошибку операции
        
        Args:
            error: Исключение, возникшее в операции
            operation_context: Контекст операции (имя, метрики, параметры)
            
        Returns:
            Словарь с результатами обработки ошибки или None
        """
        
    @abstractmethod
    def can_recover(
        self, 
        error: Exception, 
        operation_context: Dict[str, Any]
    ) -> bool:
        """
        Определить, возможно ли восстановление после ошибки
        
        Returns:
            True, если ошибка может быть исправлена автоматически
        """
        
    def on_recovery_attempt(
        self, 
        error: Exception, 
        operation_context: Dict[str, Any]
    ) -> bool:
        """
        Попытаться восстановиться после ошибки (опционально)
        
        Returns:
            True, если восстановление успешно
        """
        return False
```

### Контекст операции для обработчика ошибок
```python
operation_context = {
    "operation_name": "DECONVOLUTION",         # Название операции
    "operation_id": "uuid-string",             # Уникальный ID операции
    "start_time": datetime.now(),              # Время начала операции
    "error_time": datetime.now(),              # Время возникновения ошибки
    "thread_id": "MainThread",                 # Поток выполнения
    "call_stack": [...],                       # Стек вызовов операций
    "current_metrics": {...},                  # Метрики на момент ошибки
    "operation_parameters": {...},             # Параметры операции
    "affected_files": ["file1.csv", ...],     # Затронутые файлы
    "user_context": {...},                     # Пользовательский контекст
}
```

## Типы обработчиков ошибок

### 5.4 Стандартный логирующий обработчик
```python
class DefaultOperationErrorHandler(OperationErrorHandler):
    """Стандартный обработчик для логирования ошибок"""
    
    def handle_operation_error(self, error, operation_context):
        # Логирование ошибки с полным контекстом
        # Форматирование для таблицы операций
        # Сохранение в лог файл
        
    def can_recover(self, error, operation_context):
        # Анализ типа ошибки и возможности восстановления
        return False  # По умолчанию не восстанавливаем
```

### 5.5 Обработчик для GUI приложений
```python
class GuiOperationErrorHandler(OperationErrorHandler):
    """Обработчик с GUI уведомлениями"""
    
    def handle_operation_error(self, error, operation_context):
        # Показать диалог с ошибкой пользователю
        # Предложить варианты действий
        # Логировать пользовательский выбор
        
    def can_recover(self, error, operation_context):
        # Определить, можно ли предложить пользователю исправление
        return True  # Для известных типов ошибок
```

### 5.6 Обработчик откатов файловых операций
```python
class FileRollbackErrorHandler(OperationErrorHandler):
    """Обработчик с откатом файловых изменений"""
    
    def handle_operation_error(self, error, operation_context):
        # Откатить изменения в файлах
        # Восстановить резервные копии
        # Очистить временные файлы
        
    def on_recovery_attempt(self, error, operation_context):
        # Попытка автоматического восстановления
        return self._rollback_file_changes(operation_context)
```

## Интеграция с OperationLogger

### 5.7 Регистрация обработчиков
```python
class OperationLogger:
    def __init__(self):
        self._error_handlers: List[OperationErrorHandler] = []
        self._default_handler = DefaultOperationErrorHandler()
        
    def register_error_handler(self, handler: OperationErrorHandler):
        """Зарегистрировать обработчик ошибок"""
        self._error_handlers.append(handler)
        
    def unregister_error_handler(self, handler: OperationErrorHandler):
        """Удалить обработчик ошибок"""
        if handler in self._error_handlers:
            self._error_handlers.remove(handler)
            
    def _handle_operation_error(self, error: Exception, operation_context: dict):
        """Обработать ошибку через зарегистрированные обработчики"""
        for handler in self._error_handlers:
            try:
                result = handler.handle_operation_error(error, operation_context)
                if result and result.get('handled'):
                    break
            except Exception as handler_error:
                # Логировать ошибку в обработчике, но продолжить
                pass
        
        # Всегда вызвать стандартный обработчик
        self._default_handler.handle_operation_error(error, operation_context)
```

### 5.8 Обработка в декораторе @operation
```python
def operation(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        operation_logger = get_operation_logger()
        operation_name = func.__name__.upper()
        
        operation_logger.start_operation(operation_name)
        try:
            result = func(self, *args, **kwargs)
            operation_logger.end_operation(status="SUCCESS")
            return result
        except Exception as error:
            # Собрать контекст для обработчика ошибок
            operation_context = operation_logger.get_current_operation_context()
            
            # Вызвать обработчики ошибок
            operation_logger._handle_operation_error(error, operation_context)
            
            # Завершить операцию с ошибкой
            operation_logger.end_operation(
                status="ERROR", 
                error_info={
                    "type": type(error).__name__,
                    "message": str(error),
                    "handled": True
                }
            )
            
            # Перевыбросить исключение
            raise
    return wrapper
```

## Конфигурация обработки ошибок

### 5.9 Настройки в app_settings
```python
error_handling_config = {
    "enabled": True,                           # Включить обработку ошибок
    "show_gui_dialogs": True,                  # Показывать GUI диалоги
    "auto_recovery_attempts": 3,               # Количество попыток восстановления
    "rollback_file_changes": True,             # Откатывать изменения файлов
    "log_full_traceback": False,               # Логировать полный traceback
    "notification_channels": ["log", "gui"],   # Каналы уведомлений
    "recovery_timeout": 30.0,                  # Таймаут операций восстановления
}
```

## Ожидаемые результаты
- Расширяемый интерфейс `OperationErrorHandler`
- Автоматическая обработка ошибок операций
- Возможность подключения пользовательских обработчиков
- Базовая реализация для логирования и GUI уведомлений

## Критерии готовности
- Интерфейс `OperationErrorHandler` полностью определён
- Обработка ошибок интегрирована в декоратор `@operation`
- Реализован базовый обработчик для логирования
- Система поддерживает регистрацию множественных обработчиков

## Тестирование
- Тест обработки различных типов исключений
- Тест работы цепочки обработчиков
- Тест автоматического восстановления после ошибок
- Тест интеграции с GUI компонентами
- Тест производительности при обработке ошибок

## Документация
- Создание примеров использования обработчиков
- Документация интерфейса для разработчиков
- Руководство по созданию пользовательских обработчиков
- Лучшие практики обработки ошибок в операциях
