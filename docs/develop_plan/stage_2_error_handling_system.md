# Этап 2: Создание системы обработки ошибок

**Проект:** Open ThermoKinetics - Анализ кинетики твердофазных реакций  
**Модуль:** `src/core/log_aggregator`  
**Этап:** 2 из 4  
**Продолжительность:** 3-4 дня  
**Приоритет:** Высокий  

## Цель этапа

Создать специализированную систему для анализа и обработки ошибок подопераций с детальной категоризацией и извлечением контекстной информации.

## Задачи этапа

### 2.1 Создание базовых структур данных

**Новый файл:** `src/core/log_aggregator/error_handler.py`

**Требуемые компоненты:**

1. **Перечисление ErrorCategory:**
```python
from enum import Enum

class ErrorCategory(Enum):
    """Categories of errors that can occur in sub-operations."""
    
    COMMUNICATION_ERROR = "communication_error"
    DATA_VALIDATION_ERROR = "data_validation_error"
    FILE_OPERATION_ERROR = "file_operation_error"
    CALCULATION_ERROR = "calculation_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"
```

2. **Перечисление ErrorSeverity:**
```python
class ErrorSeverity(Enum):
    """Severity levels for sub-operation errors."""
    
    CRITICAL = "critical"  # Critical errors blocking operation
    HIGH = "high"         # Important errors affecting results
    MEDIUM = "medium"     # Moderate errors with possible workaround
    LOW = "low"           # Minor errors not affecting functionality
```

3. **Структура данных ErrorAnalysis:**
```python
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ErrorAnalysis:
    """Comprehensive analysis of a sub-operation error."""
    
    error_type: ErrorCategory
    error_message: str
    error_context: Dict[str, Any]
    severity: ErrorSeverity
    suggested_action: Optional[str] = None
    technical_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error analysis to dictionary format."""
        return {
            "type": self.error_type.value,
            "message": self.error_message,
            "context": self.error_context,
            "severity": self.severity.value,
            "suggested_action": self.suggested_action,
            "technical_details": self.technical_details
        }
```

### 2.2 Реализация SubOperationErrorHandler

**В том же файле `error_handler.py`:**

```python
class SubOperationErrorHandler:
    """
    Specialized handler for sub-operation error processing and detailed logging.
    
    Responsibilities:
    - Analyze different types of sub-operation errors
    - Extract detailed error information from response data
    - Format comprehensive error reports
    - Categorize errors by type and severity
    """
    
    def analyze_error(self, sub_operation: 'SubOperationLog') -> ErrorAnalysis:
        """
        Perform comprehensive analysis of a sub-operation error.
        
        Args:
            sub_operation: SubOperationLog instance with error status
            
        Returns:
            ErrorAnalysis: Detailed error analysis
        """
        pass
    
    def categorize_error_type(self, error_data: Any, operation_name: str, target: str) -> ErrorCategory:
        """
        Categorize error based on operation context and error data.
        
        Args:
            error_data: Raw error data from response
            operation_name: Name of the failed operation
            target: Target module of the operation
            
        Returns:
            ErrorCategory: Categorized error type
        """
        pass
    
    def extract_error_context(self, sub_operation: 'SubOperationLog') -> Dict[str, Any]:
        """
        Extract contextual information about the error.
        
        Args:
            sub_operation: SubOperationLog instance
            
        Returns:
            Dict[str, Any]: Context information for debugging
        """
        pass
    
    def determine_severity(self, error_category: ErrorCategory, error_data: Any) -> ErrorSeverity:
        """
        Determine error severity based on category and context.
        
        Args:
            error_category: Categorized error type
            error_data: Raw error data
            
        Returns:
            ErrorSeverity: Determined severity level
        """
        pass
    
    def suggest_action(self, error_analysis: ErrorAnalysis) -> Optional[str]:
        """
        Suggest corrective action based on error analysis.
        
        Args:
            error_analysis: Complete error analysis
            
        Returns:
            Optional[str]: Suggested action or None
        """
        pass
```

### 2.3 Расширение SubOperationLog

**Целевой файл:** `src/core/log_aggregator/sub_operation_log.py`

**Добавить новые поля:**

```python
from typing import Any, Dict, Optional
from .error_handler import ErrorAnalysis

@dataclass
class SubOperationLog:
    # ...существующие поля...
    
    # Новые поля для расширенной обработки ошибок
    error_details: Optional[ErrorAnalysis] = None
    exception_traceback: Optional[str] = None
    response_data_raw: Optional[Any] = None  # Для анализа ошибок
    
    def __post_init__(self):
        # ...существующий код...
        
        # Если статус Error и нет детальной информации - проанализировать
        if self.status == "Error" and self.error_details is None:
            self._analyze_error_if_needed()
    
    def _analyze_error_if_needed(self):
        """Analyze error details if status is Error and no details exist."""
        if self.response_data_raw is not None:
            from .error_handler import SubOperationErrorHandler
            error_handler = SubOperationErrorHandler()
            self.error_details = error_handler.analyze_error(self)
    
    def has_detailed_error(self) -> bool:
        """Check if detailed error information is available."""
        return self.error_details is not None
    
    def get_error_summary(self) -> str:
        """Get brief error description for table display."""
        if self.error_details:
            return f"{self.error_details.error_type.value}: {self.error_details.error_message[:50]}..."
        elif self.error_message:
            return self.error_message[:50] + "..." if len(self.error_message) > 50 else self.error_message
        else:
            return "Unknown error"
```

### 2.4 Реализация логики анализа ошибок

**В файле `error_handler.py` - детальная реализация методов:**

1. **Метод `analyze_error()`:**
```python
def analyze_error(self, sub_operation: 'SubOperationLog') -> ErrorAnalysis:
    """Perform comprehensive analysis of a sub-operation error."""
    
    # Определить категорию ошибки
    error_category = self.categorize_error_type(
        sub_operation.response_data_raw,
        sub_operation.operation_name,
        sub_operation.target
    )
    
    # Извлечь контекст ошибки
    error_context = self.extract_error_context(sub_operation)
    
    # Определить серьезность
    severity = self.determine_severity(error_category, sub_operation.response_data_raw)
    
    # Извлечь сообщение об ошибке
    error_message = self._extract_error_message(sub_operation.response_data_raw)
    
    # Создать анализ
    error_analysis = ErrorAnalysis(
        error_type=error_category,
        error_message=error_message,
        error_context=error_context,
        severity=severity,
        technical_details=self._extract_technical_details(sub_operation)
    )
    
    # Добавить предложенное действие
    error_analysis.suggested_action = self.suggest_action(error_analysis)
    
    return error_analysis
```

2. **Метод `categorize_error_type()`:**
```python
def categorize_error_type(self, error_data: Any, operation_name: str, target: str) -> ErrorCategory:
    """Categorize error based on operation context and error data."""
    
    # Анализ по типу операции
    if any(file_op in operation_name.upper() for file_op in ["LOAD", "SAVE", "EXPORT", "IMPORT"]):
        return ErrorCategory.FILE_OPERATION_ERROR
    
    if any(calc_op in operation_name.upper() for calc_op in ["CALC", "FIT", "OPTIMIZATION"]):
        return ErrorCategory.CALCULATION_ERROR
    
    if any(data_op in operation_name.upper() for data_op in ["GET", "SET", "UPDATE", "VALIDATE"]):
        return ErrorCategory.DATA_VALIDATION_ERROR
    
    # Анализ по содержимому ошибки
    if isinstance(error_data, dict):
        error_msg = str(error_data.get("error", "")).lower()
        if any(keyword in error_msg for keyword in ["not found", "missing", "invalid"]):
            return ErrorCategory.DATA_VALIDATION_ERROR
        if any(keyword in error_msg for keyword in ["connection", "timeout", "communication"]):
            return ErrorCategory.COMMUNICATION_ERROR
        if any(keyword in error_msg for keyword in ["config", "setting", "parameter"]):
            return ErrorCategory.CONFIGURATION_ERROR
    
    return ErrorCategory.UNKNOWN_ERROR
```

## Тестирование

### 2.5 Unit тесты для системы обработки ошибок

**Создать тестовый файл:** `tests/test_log_aggregator/test_error_handler.py`

**Тест-кейсы:**

1. **Тестирование ErrorAnalysis:**
```python
def test_error_analysis_creation():
    """Test ErrorAnalysis dataclass creation and serialization."""
    
def test_error_analysis_to_dict():
    """Test conversion to dictionary format."""
```

2. **Тестирование SubOperationErrorHandler:**
```python
def test_categorize_file_operation_error():
    """Test categorization of file operation errors."""
    
def test_categorize_calculation_error():
    """Test categorization of calculation errors."""
    
def test_categorize_data_validation_error():
    """Test categorization of data validation errors."""
    
def test_extract_error_context():
    """Test extraction of error context information."""
    
def test_determine_severity():
    """Test severity determination logic."""
```

3. **Тестирование интеграции с SubOperationLog:**
```python
def test_sub_operation_log_error_analysis():
    """Test automatic error analysis in SubOperationLog."""
    
def test_has_detailed_error():
    """Test detailed error detection."""
    
def test_get_error_summary():
    """Test error summary generation."""
```

## Критерии завершения этапа

- ✅ Файл `error_handler.py` создан с полной реализацией
- ✅ Перечисления `ErrorCategory` и `ErrorSeverity` определены
- ✅ Структура данных `ErrorAnalysis` реализована
- ✅ Класс `SubOperationErrorHandler` полностью функционален
- ✅ `SubOperationLog` расширен полями для обработки ошибок
- ✅ Автоматический анализ ошибок интегрирован
- ✅ Unit тесты созданы и проходят
- ✅ Интеграционные тесты обновлены
- ✅ Code review пройден

## Файлы для создания/изменения

### Новые файлы:
1. `src/core/log_aggregator/error_handler.py` - система обработки ошибок
2. `tests/test_log_aggregator/test_error_handler.py` - тесты системы ошибок

### Изменяемые файлы:
1. `src/core/log_aggregator/sub_operation_log.py` - расширение полями ошибок
2. `src/core/log_aggregator/__init__.py` - экспорт новых компонентов
3. `tests/test_log_aggregator/test_sub_operation_log.py` - обновление тестов

## Зависимости

- **Завершен Этап 1:** Улучшение отображения операций
- **Внешние библиотеки:** Нет новых зависимостей
- **Совместимость:** Полная обратная совместимость обеспечена

## Следующий этап

После завершения Этапа 2 переходить к **Этапу 3: Интеграция с форматированием**.
