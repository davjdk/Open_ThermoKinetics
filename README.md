# Open ThermoKinetics

## Introduction
**Open ThermoKinetics** is an open-source toolkit for the *isoconversional* study of solid-phase reaction kinetics. It allows you to analyze thermal analysis data (e.g., from Thermogravimetric Analysis (TGA) or Differential Scanning Calorimetry (DSC)) and determine key kinetic parameters of reactions under non-isothermal conditions. Using Open ThermoKinetics, researchers can obtain the full kinetic *“triplet”* — activation energy, pre-exponential factor, and reaction model — for each reaction stage by applying various well-established methods. The project implements all common used methods, providing a free alternative to proprietary thermokinetic software for reliable kinetic analysis.

## Implemented Methods
<div style="text-align: justify;">

Open ThermoKinetics includes implementations of numerous kinetic analysis methods, organized as follows:

+ **Model-fitting methods**:
  - [X] Direct Differential (DD)
  - [X] Coats–Redfern (CR)
+ **Model-free (isoconversional) methods:**:
  + *Differential:*
    - [X] Friedman (FR)
    - [X] Kissinger (KSG)
  + *Integral:*
    + *Approximate:*
      - [X] Ozawa–Flynn–Wall (OFW)
      - [X] Kissinger–Akahira–Sunose (KAS)
      - [X] Starink (STR)
      - [X] Vyazovkin’s nonlinear integral method (VYZ) # 0.5.0 realease
    + *Numerical:*
      - [X] Advanced isoconversional method by Vyazovkin (AIC)
      - [X] Average linear integral method (ALIM) # 0.5.0 realease
+ **Kinetic Compensation Effect (KCE)** # 0.4.0 realease
+ **Master Plots (f(α), g(α), Z(α))**
+ **Model-based methods** # 0.3.0 realease
+ **Predictions**: # 0.4.0 realease
  + *Differential methods:*
    - [X] Roduit's equation
  + *Integral methods:*
    - [X] Vyazovkin's equation
    - [X] Farjas's equation


Data preparation
+ **Deconvolution functions**:
  - [X] Gaussian
  - [X] Fraser-Suzuki
  - [X] Asymmetric double sigmoid


</div>

## Getting Started
To start using Open ThermoKinetics, follow these steps to install the software from the latest release:

1. **Download the latest release:**  
   Visit the project’s **Releases** page (on GitHub or the project website) and download the latest release package for your platform. This may be a compressed archive (ZIP/TAR) or an installer/executable for the tool.

2. **Load TGA data:**

## Логирование и диагностика

Open ThermoKinetics включает комплексную систему логирования для отслеживания операций и диагностики проблем:

### Уровни логирования
- **Базовое логирование**: Автоматически записывается в `logs/solid_state_kinetics.log`
- **Агрегированное логирование операций**: Детальные отчеты выполнения в `logs/aggregated_operations.log`

### Агрегированные логи операций
Система автоматически отслеживает все ключевые операции с детализацией:
- ⏱️ **Время выполнения** каждой операции и подоперации
- 📊 **Статус операций** (успешно/с ошибками)
- 🔍 **Типы данных** результатов (DataFrame, bool, dict, etc.)
- 📋 **Подробные таблицы** с пошаговым выполнением

**Пример агрегированного лога:**
```
================================================================================
Operation "ADD_REACTION" – STARTED (id=2, 2025-06-15 23:01:05)

+--------+----------------------+-----------+--------------------+----------+-----------+
|   Step | Sub-operation        | Target    | Result data type   |  Status  |   Time, s |
+========+======================+===========+====================+==========+===========+
|      1 | OperationType.CHE... | file_data | bool               |    OK    |     0.001 |
+--------+----------------------+-----------+--------------------+----------+-----------+
|      2 | OperationType.GET... | file_data | DataFrame          |    OK    |     0.003 |
+--------+----------------------+-----------+--------------------+----------+-----------+

SUMMARY: steps 2, successful 2, with errors 0, total time 0.005 s.
Operation "ADD_REACTION" – COMPLETED (status: successful)
================================================================================
```

### Troubleshooting
При возникновении проблем:
1. 🔍 **Проверьте логи** в папке `logs/`
2. 📋 **Агрегированные логи** покажут, на каком этапе произошла ошибка
3. 🐛 **Базовые логи** содержат подробные стеки ошибок
4. ⚙️ **Уровень логирования** можно настроить в `src/core/logger_config.py`

---