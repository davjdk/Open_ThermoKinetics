# Этап 6: Интеграция операций в основной код приложения

## Цель этапа
Внедрить явное логирование операций во все ключевые места кода приложения и обеспечить корректную работу новой системы агрегации логов.

## Компоненты для модификации

### 6.1. MainWindow - интеграция операций
Модифицировать все обработчики операций в `src/gui/main_window.py`:

#### Сложные операции (3+ handle_request_cycle):

##### ADD_NEW_SERIES - самая сложная операция:
```python
@operation("ADD_NEW_SERIES")
def _handle_add_new_series(self, params):
    """Добавление новой серии данных"""
    # Метрика пользовательского действия
    operation_logger.add_metric("user_action", "add_series")
    operation_logger.add_metric("initiated_by", "main_window")
    
    # Подоперация 1: Получение данных всех файлов
    df_copies = self.handle_request_cycle("file_data", OperationType.GET_ALL_DATA, file_name="all_files")
    
    # Открытие диалога выбора файлов
    series_name, selected_files = self.main_tab.sidebar.open_add_series_dialog(df_copies)
    if not series_name or not selected_files:
        operation_logger.add_metric("user_cancelled", True)
        logger.warning(f"{self.actor_name} user canceled or gave invalid input for new series.")
        return

    # Метрики выбранных данных
    operation_logger.add_metric("series_name", series_name)
    operation_logger.add_metric("file_count", len(selected_files))
    operation_logger.add_metric("heating_rates", [rate for _, rate, _ in selected_files])

    # Подоперация 2: Обработка и объединение данных
    df_with_rates = {}
    experimental_masses = []
    for file_name, heating_rate, mass in selected_files:
        experimental_masses.append(mass)
        # ... существующий код обработки данных
    
    operation_logger.add_metric("experimental_masses", experimental_masses)

    # Подоперация 3: Объединение данных и построение графика
    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on="temperature", how="outer"), 
        df_with_rates.values()
    )
    merged_df.sort_values(by="temperature", inplace=True)
    merged_df.interpolate(method="linear", inplace=True)

    operation_logger.add_metric("merged_data_points", len(merged_df))
    self.main_tab.plot_canvas.plot_data_from_dataframe(merged_df)

    # Подоперация 4: Добавление серии в систему
    is_ok = self.handle_request_cycle(
        "series_data",
        OperationType.ADD_NEW_SERIES,
        experimental_masses=experimental_masses,
        data=merged_df,
        name=series_name,
    )

    if is_ok:
        operation_logger.add_metric("series_added_successfully", True)
        self.main_tab.sidebar.add_series(series_name)
        
        # Подоперация 5: Получение схемы реакций
        series_entry = self.handle_request_cycle(
            "series_data", OperationType.GET_SERIES, series_name=series_name, info_type="all"
        )
        
        if series_entry["reaction_scheme"]:
            operation_logger.add_metric("reaction_scheme_found", True)
            self.main_tab.sub_sidebar.model_based.update_scheme_data(series_entry["reaction_scheme"])
            self.main_tab.sub_sidebar.model_based.update_calculation_settings(series_entry["calculation_settings"])
        else:
            operation_logger.add_metric("reaction_scheme_found", False)
            logger.warning("It was not possible to obtain a reaction diagram for added series.")
    else:
        operation_logger.add_metric("series_added_successfully", False)
        logger.error(f"Couldn't add a series: {series_name}")
```

##### MODEL_FREE_CALCULATION:
```python
@operation("MODEL_FREE_CALCULATION")
def _handle_model_free_calculation(self, params: dict):
    """Model-Free расчеты кинетических параметров"""
    series_name = params.get("series_name")
    operation_logger.add_metric("series_name", series_name)
    operation_logger.add_metric("calculation_method", params.get("fit_method", "unknown"))
    
    if not series_name:
        operation_logger.add_metric("error", "no_series_name")
        console.print_error("Не указано имя серии для расчета")
        return

    # Подоперация 1: Получение данных серии
    series_entry = self.handle_request_cycle(
        "series_data", OperationType.GET_SERIES, series_name=series_name, info_type="all"
    )
    experimental_df = series_entry.get("experimental_data")
    deconvolution_results = series_entry.get("deconvolution_results", {})
    
    operation_logger.add_metric("has_experimental_data", experimental_df is not None)
    operation_logger.add_metric("has_deconvolution_results", bool(deconvolution_results))
    
    if not deconvolution_results:
        operation_logger.add_metric("error", "no_deconvolution_results")
        console.print_error("Отсутствуют результаты деконволюции для серии")
        return

    # Подоперация 2: Подготовка данных реакций
    reactions, _ = self.main_tab.sub_sidebar.series_sub_bar.check_missing_reactions(
        experimental_df, deconvolution_results
    )
    operation_logger.add_metric("reactions_count", len(reactions))
    
    params["reaction_data"] = {
        reaction: self.main_tab.sub_sidebar.series_sub_bar.get_reaction_dataframe(
            experimental_df, deconvolution_results, reaction_n=reaction
        )
        for reaction in reactions
    }

    # Подоперация 3: Выполнение Model-Free расчетов
    fit_results = self.handle_request_cycle(
        "model_free_calculation", OperationType.MODEL_FREE_CALCULATION, calculation_params=params
    )
    
    if not fit_results:
        operation_logger.add_metric("calculation_successful", False)
        console.print_error("Ошибка выполнения Model-Free расчетов")
        return
    
    operation_logger.add_metric("calculation_successful", True)
    operation_logger.add_metric("results_count", len(fit_results) if isinstance(fit_results, dict) else 0)

    # Подоперация 4: Сохранение результатов
    update_data = {"model_free_results": {params["fit_method"]: fit_results}}
    self.handle_request_cycle(
        "series_data", OperationType.UPDATE_SERIES, series_name=series_name, update_data=update_data
    )
    
    self.main_tab.sub_sidebar.model_free_sub_bar.update_fit_results(fit_results)
    operation_logger.add_metric("results_saved", True)
```

#### Средние операции (2 handle_request_cycle):

##### LOAD_DECONVOLUTION_RESULTS:
```python
@operation("LOAD_DECONVOLUTION_RESULTS")
def _handle_load_deconvolution_results(self, params: dict):
    """Загрузка результатов деконволюции"""
    series_name = params.get("series_name")
    operation_logger.add_metric("series_name", series_name)
    
    if not series_name:
        operation_logger.add_metric("error", "no_series_name")
        console.print_error("Не указано имя серии")
        return

    deconvolution_results = params.get("deconvolution_results", {})
    operation_logger.add_metric("results_count", len(deconvolution_results))
    
    # Подоперация 1: Обновление серии результатами
    update_data = {"deconvolution_results": deconvolution_results}
    is_ok = self.handle_request_cycle(
        "series_data",
        OperationType.UPDATE_SERIES,
        series_name=series_name,
        update_data=update_data,
    )
    
    if not is_ok:
        operation_logger.add_metric("update_successful", False)
        console.print_error("Не удалось обновить серию результатами деконволюции")
        return
    
    operation_logger.add_metric("update_successful", True)
    
    # Подоперация 2: Выбор серии для отображения
    self._handle_select_series(params)
```

##### SELECT_SERIES:
```python
@operation("SELECT_SERIES")
def _handle_select_series(self, params: dict):
    """Выбор серии для работы"""
    series_name = params.get("series_name")
    operation_logger.add_metric("series_name", series_name)
    
    if not series_name:
        operation_logger.add_metric("error", "no_series_name")
        console.print_error("Не указано имя серии")
        return

    # Подоперация 1: Получение данных серии
    series_entry = self.handle_request_cycle(
        "series_data", OperationType.GET_SERIES, series_name=series_name, info_type="all"
    )
    
    if not series_entry:
        operation_logger.add_metric("series_found", False)
        console.print_error(f"Серия '{series_name}' не найдена")
        return
    
    operation_logger.add_metric("series_found", True)
    
    # Извлечение компонентов серии
    reaction_scheme = series_entry.get("reaction_scheme")
    calculation_settings = series_entry.get("calculation_settings")
    series_df = series_entry.get("experimental_data")
    deconvolution_results = series_entry.get("deconvolution_results", {})
    
    operation_logger.add_metric("has_reaction_scheme", reaction_scheme is not None)
    operation_logger.add_metric("has_deconvolution_results", bool(deconvolution_results))
    operation_logger.add_metric("data_points", len(series_df) if series_df is not None else 0)

    if not reaction_scheme:
        operation_logger.add_metric("scheme_status", "missing")
        console.print_warning("Отсутствует схема реакций для серии")
        return

    # Подоперация 2: Обновление UI
    if deconvolution_results == {}:
        operation_logger.add_metric("deconvolution_status", "missing")
        console.print_warning("Отсутствуют результаты деконволюции")
    else:
        operation_logger.add_metric("deconvolution_status", "available")
        operation_logger.add_metric("reactions_count", len(deconvolution_results))
    
    self.main_tab.sub_sidebar.model_based.update_scheme_data(reaction_scheme)
    self.main_tab.sub_sidebar.model_based.update_calculation_settings(calculation_settings)
    self.main_tab.sub_sidebar.series_sub_bar.update_series_ui(series_df, deconvolution_results)
    
    operation_logger.add_metric("ui_updated", True)
```

#### Простые операции (1 handle_request_cycle):

##### DECONVOLUTION:
```python
@operation("DECONVOLUTION")
def _handle_deconvolution(self, params):
    """Деконволюция пиков"""
    operation_logger.add_metric("file_name", params.get("file_name", "unknown"))
    operation_logger.add_metric("method", "peak_deconvolution")
    
    # Единственная подоперация: выполнение деконволюции
    data = self.handle_request_cycle("calculations_data_operations", OperationType.DECONVOLUTION, **params)
    
    if data:
        operation_logger.add_metric("deconvolution_successful", True)
        # Попытка извлечь метрики из результата
        if isinstance(data, dict):
            operation_logger.add_metric("reactions_found", len(data.get("reactions", [])))
            operation_logger.add_metric("final_mse", data.get("mse", None))
    else:
        operation_logger.add_metric("deconvolution_successful", False)
    
    logger.debug(f"Deconvolution result: {data}")
```

##### ADD_REACTION и REMOVE_REACTION:
```python
@operation("ADD_REACTION")
def _handle_add_reaction(self, params):
    """Добавление реакции"""
    operation_logger.add_metric("reaction_function", params.get("function", "unknown"))
    operation_logger.add_metric("file_name", params.get("file_name", "unknown"))
    
    is_ok = self.handle_request_cycle("calculations_data_operations", OperationType.ADD_REACTION, **params)
    operation_logger.add_metric("reaction_added", is_ok)
    
    if not is_ok:
        console.print_error("Не удалось добавить реакцию")

@operation("REMOVE_REACTION")
def _handle_remove_reaction(self, params):
    """Удаление реакции"""
    operation_logger.add_metric("reaction_name", params.get("reaction_name", "unknown"))
    operation_logger.add_metric("file_name", params.get("file_name", "unknown"))
    
    is_ok = self.handle_request_cycle("calculations_data_operations", OperationType.REMOVE_REACTION, **params)
    operation_logger.add_metric("reaction_removed", is_ok)
    
    if not is_ok:
        console.print_error("Не удалось удалить реакцию")
    
    logger.debug(f"{OperationType.REMOVE_REACTION=} {is_ok=}")
```

### 6.2. Интеграция с другими компонентами

#### GUI компоненты - добавление метрик UI:
```python
# В различных GUI компонентах добавить метрики взаимодействия
class DeconvolutionPanel:
    def on_calculation_started(self):
        """При начале расчета деконволюции"""
        if hasattr(self, 'current_operation'):
            operation_logger.add_metric("ui_component", "deconvolution_panel")
            operation_logger.add_metric("calculation_triggered_by", "ui_button")

class ModelBasedPanel:
    def on_optimization_started(self):
        """При начале оптимизации"""
        if hasattr(self, 'current_operation'):
            operation_logger.add_metric("ui_component", "model_based_panel")
            operation_logger.add_metric("optimization_method", self.get_selected_method())
```

#### Calculations - расширение для метрик:
```python
class Calculations:
    @operation("OPTIMIZATION_PROCESS")
    def perform_optimization(self, params):
        """Долгосрочный процесс оптимизации"""
        operation_logger.add_metric("optimization_algorithm", params.get("algorithm", "unknown"))
        operation_logger.add_metric("max_iterations", params.get("max_iter", 0))
        
        # Периодическое обновление метрик в процессе оптимизации
        for iteration in range(params.get("max_iter", 0)):
            # ... логика оптимизации
            if iteration % 10 == 0:  # Каждые 10 итераций
                operation_logger.add_metric(f"iteration_{iteration}", {
                    "current_error": current_error,
                    "parameters": current_params
                })
```

### 6.3. Обработка ошибок и исключений

#### Wrapper для операций с обработкой ошибок:
```python
def safe_operation(operation_name: str):
    """Декоратор для безопасного выполнения операций"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with log_operation(operation_name):
                    operation_logger.add_metric("operation_start_time", time.time())
                    result = func(*args, **kwargs)
                    operation_logger.add_metric("operation_successful", True)
                    return result
            except Exception as e:
                operation_logger.add_metric("operation_successful", False)
                operation_logger.add_metric("error_type", type(e).__name__)
                operation_logger.add_metric("error_message", str(e))
                logger.error(f"Error in operation {operation_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

# Применение к критичным операциям
@safe_operation("CRITICAL_CALCULATION")
def _handle_critical_calculation(self, params):
    # ... код операции
```

### 6.4. Настройка конфигурации

#### Обновление конфигурации логирования:
```python
# В logger_config.py
def configure_operation_logging():
    """Настроить логирование операций"""
    
    # Включить агрегацию операций
    aggregation_config = AggregationConfig(
        enable_operation_monitoring=True,
        operation_aggregation_enabled=True,
        explicit_mode_enabled=True,
        auto_mode_enabled=True,
        operation_timeout=30.0
    )
    
    # Настроить форматирование операций
    formatting_config = OperationFormattingConfig(
        enabled=True,
        show_sub_operations=True,
        show_custom_metrics=True,
        precision_seconds=3,
        precision_metrics=6
    )
    
    # Применить конфигурацию
    LoggerManager.configure_logging(
        enable_aggregation=True,
        aggregation_config=aggregation_config,
        operation_formatting_config=formatting_config
    )
```

### 6.5. Тестирование интеграции

#### Unit-тесты для операций:
```python
class TestOperationIntegration:
    def test_add_new_series_operation(self):
        """Тест операции добавления серии"""
        with patch('src.gui.main_window.operation_logger') as mock_logger:
            main_window = MainWindow(signals)
            
            # Симуляция добавления серии
            params = {"test": "data"}
            main_window._handle_add_new_series(params)
            
            # Проверка вызовов метрик
            mock_logger.add_metric.assert_any_call("user_action", "add_series")
            mock_logger.add_metric.assert_any_call("initiated_by", "main_window")
    
    def test_deconvolution_operation(self):
        """Тест операции деконволюции"""
        with patch('src.gui.main_window.operation_logger') as mock_logger:
            main_window = MainWindow(signals)
            
            params = {"file_name": "test.csv"}
            main_window._handle_deconvolution(params)
            
            # Проверка метрик деконволюции
            mock_logger.add_metric.assert_any_call("file_name", "test.csv")
            mock_logger.add_metric.assert_any_call("method", "peak_deconvolution")
```

#### Интеграционные тесты:
```python
class TestOperationAggregationE2E:
    def test_full_operation_lifecycle(self):
        """Тест полного жизненного цикла операции"""
        
        # Настроить систему логирования
        configure_operation_logging()
        
        # Выполнить операцию
        with log_operation("TEST_OPERATION"):
            operation_logger.add_metric("test_metric", "test_value")
            logger.info("Test operation step 1")
            logger.info("Test operation step 2")
        
        # Проверить, что таблица была сгенерирована
        # (проверка через mock или анализ лог-файлов)
```

## Критерии завершения этапа
1. ✅ Все основные операции в MainWindow обернуты в `@operation` декораторы
2. ✅ Добавлены релевантные метрики для каждого типа операции
3. ✅ Реализована обработка ошибок в операциях
4. ✅ Интегрированы GUI компоненты для добавления UI метрик
5. ✅ Обновлена конфигурация логирования для поддержки операций
6. ✅ Написаны unit-тесты для всех модифицированных методов
7. ✅ Проведены интеграционные тесты полного жизненного цикла операций
8. ✅ Проверена совместимость с существующей системой логирования

## Ожидаемый результат
После завершения этапа все ключевые пользовательские действия в приложении будут автоматически отслеживаться как явные операции с детальными метриками, и система будет генерировать структурированные таблицы операций в агрегированном логе для анализа и отладки.
