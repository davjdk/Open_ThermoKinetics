# Этап 3: UI компоненты для basinhopping

## Описание этапа

Третий этап посвящён созданию и интеграции пользовательского интерфейса для настройки и запуска метода basinhopping в ModelBasedPanel. Этот этап обеспечивает пользователю возможность выбора метода оптимизации, настройки всех параметров basinhopping и визуального контроля процесса.

## Цели этапа

- **Добавить выбор метода оптимизации** (differential_evolution/basinhopping) в ModelBasedPanel
- **Реализовать UI для параметров basinhopping**: T, niter, stepsize, batch_size, minimizer_method
- **Обеспечить динамическое отображение**: параметры basinhopping видимы только при выборе соответствующего метода
- **Валидация параметров**: диапазоны, типы, ограничения
- **Интеграция с backend**: корректная передача параметров в ModelBasedScenario
- **UI/UX тесты**: проверка корректности отображения, передачи и валидации параметров

## Зависимости

- ✅ **Этап 2 завершён**: backend поддержка basinhopping полностью интегрирована
- ✅ **ModelBasedPanel**: существующий UI для model-based анализа

## Архитектура решения

### Расширение ModelBasedPanel

**Файл**: `src/gui/main_tab/sub_sidebar/model_based/model_based_panel.py`

- Добавить ComboBox для выбора метода оптимизации
- Добавить QGroupBox с параметрами basinhopping (T, niter, stepsize, batch_size, minimizer_method)
- Динамически показывать/скрывать параметры в зависимости от выбранного метода
- Обновить метод get_method_params для передачи всех параметров backend
- Валидация значений перед запуском расчёта

### Пример полной структуры UI (из ТЗ)

```python
class ModelBasedPanel(QWidget):
    """Расширение existing ModelBasedPanel для поддержки basinhopping"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        
    def _init_ui(self):
        # ...existing code...
        
        # Добавление выбора метода оптимизации
        self._add_optimization_method_selection()
        
        # Группа параметров basinhopping (изначально скрыта)
        self._add_basinhopping_parameters()
        
    def _add_optimization_method_selection(self):
        """Добавление ComboBox для выбора метода оптимизации"""
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Optimization Method:"))
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["differential_evolution", "basinhopping"])
        self.method_combo.currentTextChanged.connect(self._on_method_changed)
        method_layout.addWidget(self.method_combo)
        
        self.main_layout.addLayout(method_layout)
    
    def _add_basinhopping_parameters(self):
        """Создание группы параметров для basinhopping"""
        self.basinhopping_group = QGroupBox("Basin-Hopping Parameters")
        self.basinhopping_group.setVisible(False)  # Изначально скрыта
        
        params_layout = QFormLayout()
        
        # Temperature parameter (T)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.1, 10.0)
        self.temperature_spin.setValue(1.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        params_layout.addRow("Temperature (T):", self.temperature_spin)
        
        # Number of iterations (niter)
        self.niter_spin = QSpinBox()
        self.niter_spin.setRange(10, 1000)
        self.niter_spin.setValue(100)
        params_layout.addRow("Iterations (niter):", self.niter_spin)
        
        # Step size (stepsize)
        self.stepsize_spin = QDoubleSpinBox()
        self.stepsize_spin.setRange(0.01, 2.0)
        self.stepsize_spin.setValue(0.5)
        self.stepsize_spin.setSingleStep(0.01)
        self.stepsize_spin.setDecimals(3)
        params_layout.addRow("Step Size:", self.stepsize_spin)
        
        # Batch size for Batch-Stepper (batch_size)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(2, 16)
        self.batch_size_spin.setValue(min(4, os.cpu_count()))
        params_layout.addRow("Batch Size:", self.batch_size_spin)
        
        # Local minimizer method (minimizer_method)
        self.minimizer_combo = QComboBox()
        self.minimizer_combo.addItems(["L-BFGS-B", "SLSQP", "TNC", "trust-constr"])
        params_layout.addRow("Local Minimizer:", self.minimizer_combo)
        
        self.basinhopping_group.setLayout(params_layout)
        self.main_layout.addWidget(self.basinhopping_group)
    
    def _on_method_changed(self, method_name: str):
        """Обработка изменения метода оптимизации"""
        is_basinhopping = (method_name == "basinhopping")
        self.basinhopping_group.setVisible(is_basinhopping)
        
        # Обновление размеров окна при смене видимости
        self.adjustSize()
    
    def get_method_params(self) -> dict:
        """Получение параметров для выбранного метода оптимизации"""
        base_params = self._get_base_method_params()  # Existing method
        
        method = self.method_combo.currentText()
        base_params['optimization_method'] = method
        
        if method == "basinhopping":
            # Добавление специфичных параметров basinhopping
            base_params.update({
                'T': self.temperature_spin.value(),
                'niter': self.niter_spin.value(),
                'stepsize': self.stepsize_spin.value(),
                'batch_size': self.batch_size_spin.value(),
                'minimizer_method': self.minimizer_combo.currentText()
            })
        
        return base_params
```

### Валидация параметров

- Диапазоны и типы для каждого параметра (см. BASINHOPPING_PARAM_RANGES)
- Проверка batch_size <= CPU count  
- Проверка корректности minimizer_method

### Интеграция с backend

- Передача всех параметров через get_method_params
- Проверка, что параметры корректно доходят до ModelBasedScenario
- UI тесты на корректность передачи

## Критерии приемки

### Функциональные тесты

1. **Выбор метода**:
   - ✅ ComboBox корректно переключает методы
   - ✅ Параметры basinhopping видимы только при выборе этого метода
   - ✅ По умолчанию выбран differential_evolution (backward compatibility)

2. **Параметры basinhopping**:
   - ✅ Все поля имеют корректные диапазоны и значения по умолчанию
   - ✅ Валидация предотвращает некорректные значения
   - ✅ batch_size автоматически адаптируется к количеству CPU

3. **Передача параметров**:
   - ✅ Все параметры передаются backend через get_method_params
   - ✅ Некорректные значения не допускаются до backend
   - ✅ Backward compatibility: differential_evolution работает без изменений

### UI/UX тесты

1. **Динамическое отображение**:
   - ✅ Корректное отображение и скрытие параметров basinhopping
   - ✅ Размеры окна адаптируются при переключении методов
   - ✅ Сообщения об ошибках при неверных значениях

2. **Пользовательский опыт**:
   - ✅ Интуитивно понятные названия параметров и подсказки
   - ✅ Разумные значения по умолчанию
   - ✅ Плавное переключение между методами

### Интеграционные тесты

**Файл**: `tests/test_model_based_panel_ui.py`

```python
import pytest
from PyQt6.QtWidgets import QApplication
from src.gui.main_tab.sub_sidebar.model_based.model_based_panel import ModelBasedPanel

class TestModelBasedPanelUI:
    """Тестирование UI компонентов basinhopping"""
    
    def test_method_switching(self):
        """Тест переключения между методами оптимизации"""
        
    def test_parameter_validation(self):
        """Тест валидации диапазонов и типов параметров"""
        
    def test_parameter_passing(self):
        """Тест корректной передачи параметров в backend"""
        
    def test_dynamic_visibility(self):
        """Тест динамического отображения/скрытия параметров"""
        
    def test_default_values(self):
        """Тест значений по умолчанию для всех параметров"""
        
    def test_ui_layout_adaptation(self):
        """Тест адаптации размеров при переключении методов"""
```

### Тестирование взаимодействия с backend

**Файл**: `tests/test_ui_backend_integration.py`

```python
def test_parameter_flow_differential_evolution():
    """Тест передачи параметров differential_evolution (existing)"""
    
def test_parameter_flow_basinhopping():
    """Тест передачи всех параметров basinhopping в backend"""
    
def test_parameter_validation_backend():
    """Тест, что backend корректно получает валидированные параметры"""
    
def test_error_handling():
    """Тест обработки ошибок от backend в UI"""
```

## Результаты этапа

### Deliverables

1. **Расширенный ModelBasedPanel** с поддержкой basinhopping UI
2. **UI тесты** (модульные и интеграционные) 
3. **Документация** (docstrings, примеры, обновление user guide)
4. **Валидация параметров** с корректными диапазонами и ограничениями

### Метрики качества

- **Test Coverage**: ≥95% для новых UI компонентов
- **UI Responsiveness**: Плавное переключение между методами
- **Parameter Validation**: 100% корректная валидация всех параметров
- **Backend Integration**: Корректная передача всех параметров

## Pull Request критерии

### Обязательные проверки

1. ✅ **Все UI тесты проходят** (модульные + интеграционные)
2. ✅ **Корректная интеграция с backend** - параметры передаются правильно
3. ✅ **Backward compatibility** - differential_evolution UI без изменений
4. ✅ **Валидация параметров** - некорректные значения блокируются
5. ✅ **Полная документация** и примеры

### Дополнительные проверки

- ✅ **Cross-platform UI тестирование** (Windows + Linux)
- ✅ **UI/UX проверки** - интуитивность и удобство использования
- ✅ **Линтеры и code style** (flake8, mypy, black)
- ✅ **Регрессионные тесты** - existing UI functionality

## Следующий этап

После завершения **Этапа 3** пользовательский интерфейс для basinhopping будет полностью готов. **Этап 4: Интеграционное тестирование и документация** завершит внедрение.
