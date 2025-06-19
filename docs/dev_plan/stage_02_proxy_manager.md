# Этап 2: Создание прокси-менеджера процесса

## Описание этапа

Реализация класса-прокси для управления процессом-работником из главного потока GUI. Прокси будет отвечать за запуск процесса, мониторинг результатов через QTimer и интеграцию с системой сигналов Qt.

## Задачи этапа

### 1. Создание класса ModelCalcProxy

**Файл:** `src/core/model_calc_proxy.py`

Реализовать менеджер процесса с функциями:
- Запуск и остановка процесса-работника
- Мониторинг очереди результатов через QTimer
- Интеграция с сигналами Qt (`new_best_result`)
- Обработка завершения процесса

```python
from PyQt6.QtCore import QTimer, QObject
import multiprocessing
from .model_calc_worker import run_model_calc

class ModelCalcProxy:
    """
    Прокси-менеджер для управления процессом model-based расчетов.
    
    Отвечает за:
    - Запуск процесса-работника
    - Мониторинг результатов через QTimer
    - Интеграцию с Qt сигналами
    - Корректное завершение процесса
    """
    
    def __init__(self, calculations_obj):
        """
        Args:
            calculations_obj: Экземпляр Calculations для эмиссии сигналов
        """
        self.calculations = calculations_obj
        self.process = None
        self.queue = None
        self.timer = None
        
    def start_process(self, target_func, bounds, method_params):
        """
        Запуск процесса-работника для model-based расчета.
        
        Args:
            target_func: Объект ModelBasedTargetFunction
            bounds: Границы параметров оптимизации
            method_params: Параметры алгоритма дифференциальной эволюции
        """
        # Очистка предыдущего состояния
        if self.process and self.process.is_alive():
            self.stop_process()
            
        # Подготовка межпроцессной коммуникации
        self.calculations.stop_event.clear()
        self.queue = multiprocessing.Queue()
        
        # Создание и запуск процесса
        self.process = multiprocessing.Process(
            target=run_model_calc,
            args=(target_func, bounds, method_params, 
                  self.calculations.stop_event, self.queue)
        )
        self.process.start()
        
        # Запуск мониторинга результатов
        self._start_queue_monitoring()
        
    def _start_queue_monitoring(self):
        """Запуск таймера для мониторинга очереди результатов."""
        self.timer = QTimer()
        self.timer.setInterval(100)  # Проверка каждые 100 мс
        self.timer.timeout.connect(self._poll_queue)
        self.timer.start()
        
    def _poll_queue(self):
        """Обработка сообщений из очереди результатов."""
        # Чтение всех доступных сообщений
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                self._handle_message(msg)
            except:
                break
                
        # Проверка состояния процесса
        if self.process and not self.process.is_alive():
            self._handle_process_finished()
            
    def _handle_message(self, msg):
        """
        Обработка отдельного сообщения из очереди.
        
        Args:
            msg: Сообщение от процесса-работника
        """
        if isinstance(msg, dict):
            if "best_mse" in msg and "params" in msg:
                # Промежуточный результат
                self.calculations.new_best_result.emit(msg)
                
            elif "final_result" in msg:
                # Финальный результат оптимизации
                result = msg["final_result"]
                self._finish_process(result)
                
            elif "error" in msg:
                # Ошибка в процессе
                error = Exception(msg["error"])
                self._finish_process(error)
                
    def _handle_process_finished(self):
        """Обработка завершения процесса без финального сообщения."""
        if self.process.exitcode != 0:
            # Процесс завершился с ошибкой или был прерван
            self._finish_process(Exception("Process terminated"))
            
    def _finish_process(self, result_obj):
        """
        Завершение работы с процессом и уведомление Calculations.
        
        Args:
            result_obj: Результат оптимизации или объект исключения
        """
        # Остановка мониторинга
        if self.timer:
            self.timer.stop()
            self.timer = None
            
        # Завершение процесса
        if self.process and self.process.is_alive():
            self.process.terminate()
            
        if self.process:
            self.process.join(timeout=1.0)
            self.process = None
            
        # Очистка очереди
        self.queue = None
        
        # Уведомление Calculations о завершении
        self.calculations._calculation_finished(result_obj)
        
    def stop_process(self):
        """
        Остановка выполняющегося процесса.
        
        Returns:
            bool: True если процесс был остановлен, False если не было активного процесса
        """
        if self.process and self.process.is_alive():
            # Установка флага остановки
            self.calculations.stop_event.set()
            
            # Отложенное принудительное завершение
            QTimer.singleShot(200, self._force_terminate)
            return True
            
        return False
        
    def _force_terminate(self):
        """Принудительное завершение процесса если он не остановился."""
        if self.process and self.process.is_alive():
            self.process.terminate()
```

### 2. Интеграция с архитектурой логирования

Добавить поддержку системы логирования операций:

```python
from src.core.log_aggregator import operation

class ModelCalcProxy:
    # ...existing code...
    
    @operation
    def start_process(self, target_func, bounds, method_params):
        """Запуск процесса с логированием операции."""
        # ...implementation...
```

### 3. Обработка ошибок и edge cases

Реализовать обработку различных сценариев:
- Повторный запуск процесса
- Множественные вызовы stop_process
- Сбои в межпроцессной коммуникации
- Утечки ресурсов

### 4. Тестирование прокси-менеджера

**Файл:** `tests/test_model_calc_proxy.py`

```python
import unittest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QTimer
from src.core.model_calc_proxy import ModelCalcProxy

class TestModelCalcProxy(unittest.TestCase):
    
    def setUp(self):
        self.mock_calculations = Mock()
        self.proxy = ModelCalcProxy(self.mock_calculations)
        
    def test_process_startup(self):
        """Тест запуска процесса."""
        pass
        
    def test_queue_monitoring(self):
        """Тест мониторинга очереди через QTimer."""
        pass
        
    def test_message_handling(self):
        """Тест обработки различных типов сообщений."""
        pass
        
    def test_process_termination(self):
        """Тест корректного завершения процесса."""
        pass
        
    def test_signal_integration(self):
        """Тест интеграции с Qt сигналами."""
        pass
```

## Критерии приемки

1. ✅ Создан класс `ModelCalcProxy` с полным API
2. ✅ Реализован запуск и мониторинг процесса-работника
3. ✅ QTimer корректно обрабатывает очередь результатов
4. ✅ Интеграция с сигналами Qt работает без ошибок
5. ✅ Процесс корректно завершается во всех сценариях
6. ✅ Обработаны edge cases и ошибки
7. ✅ Написаны comprehensive тесты
8. ✅ Нет утечек ресурсов при повторных запусках

## Результат этапа

- Готовый класс ModelCalcProxy
- Полная интеграция с Qt event loop
- Comprehensive тест-покрытие
- Обработка всех edge cases
- Документация API прокси-менеджера

## Pull Request

**Название:** `feat: add ModelCalcProxy for process management`

**Описание:**
```
Добавлен прокси-менеджер для управления процессом model-based расчетов:

- Создан класс ModelCalcProxy для управления worker процессом
- Реализован мониторинг результатов через QTimer (каждые 100ms)
- Добавлена интеграция с Qt сигналами (new_best_result)
- Реализована корректная остановка процесса (graceful + terminate)
- Обработаны edge cases и предотвращены утечки ресурсов
- Написаны comprehensive unit-тесты

Прокси готов для интеграции с классом Calculations.
```

**Связанные файлы:**
- `src/core/model_calc_proxy.py` (новый)
- `tests/test_model_calc_proxy.py` (новый)
- `docs/dev_plan/stage_02_proxy_manager.md` (новый)
