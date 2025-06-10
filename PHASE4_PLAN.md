# 🎯 ПЛАН ФАЗЫ 4: Data Layer (Слой данных)

## 🎯 Цель Фазы 4
Создать структурированные данные контента для User Guide Framework - JSON файлы с контентом разделов, навигационную структуру и мультиязычный контент.

## 📋 Объем работ

### 4.1 Создание структуры данных
- **Навигационная структура** (`toc.json`) - оглавление с иерархией разделов
- **Файлы контента** (`content/*.json`) - структурированный контент каждого раздела
- **Языковые файлы** (`lang/*.json`) - переводы интерфейса
- **Файлы тем** (`themes/*.json`) - дополнительные темы оформления

### 4.2 Структура директорий данных
```
src/gui/user_guide_framework/data/
├── toc.json                    # Главное оглавление
├── content/                    # Контент разделов
│   ├── introduction/
│   │   ├── overview.json
│   │   ├── installation.json
│   │   └── quick_start.json
│   ├── data_management/
│   │   ├── file_loading.json
│   │   ├── data_preprocessing.json
│   │   └── file_operations.json
│   ├── analysis/
│   │   ├── deconvolution.json
│   │   ├── model_fit.json
│   │   ├── model_free.json
│   │   └── model_based.json
│   └── advanced/
│       ├── series_analysis.json
│       ├── export_import.json
│       └── troubleshooting.json
├── lang/                       # Переводы интерфейса
│   ├── ru.json
│   └── en.json
└── themes/                     # Дополнительные темы
    ├── academic.json
    └── presentation.json
```

## 📄 Схемы данных

### 4.3 Схема toc.json (Table of Contents)
```json
{
  "version": "1.0",
  "default_language": "ru",
  "supported_languages": ["ru", "en"],
  "root_sections": [
    {
      "id": "introduction",
      "title": {
        "ru": "Введение",
        "en": "Introduction"
      },
      "icon": "info-circle",
      "children": [
        {
          "id": "overview",
          "title": {
            "ru": "Обзор программы",
            "en": "Program Overview"
          },
          "content_file": "introduction/overview.json"
        }
      ]
    }
  ]
}
```

### 4.4 Схема файла контента
```json
{
  "section_id": "overview",
  "version": "1.0",
  "metadata": {
    "title": {
      "ru": "Обзор программы",
      "en": "Program Overview"
    },
    "description": {
      "ru": "Общий обзор возможностей программы",
      "en": "General overview of program capabilities"
    },
    "difficulty": "beginner",
    "estimated_time": "5 минут",
    "tags": ["overview", "introduction"]
  },
  "content": {
    "ru": [
      {
        "type": "heading",
        "level": 1,
        "text": "Обзор программы Open ThermoKinetics"
      },
      {
        "type": "paragraph",
        "text": "Open ThermoKinetics - это программа для анализа кинетики твердофазных реакций..."
      },
      {
        "type": "list",
        "items": [
          "Анализ термогравиметрических данных",
          "Деконволюция пиков",
          "Model-fit и Model-free методы"
        ]
      }
    ],
    "en": [
      {
        "type": "heading",
        "level": 1,
        "text": "Open ThermoKinetics Program Overview"
      }
    ]
  },
  "related_sections": ["quick_start", "installation"]
}
```

## 🛠 Задачи реализации

### 4.5 Основные задачи

#### Задача 4.1: Создание базовой структуры данных
- [ ] Создать директорию `src/gui/user_guide_framework/data/`
- [ ] Создать файл `toc.json` с навигационной структурой
- [ ] Создать поддиректории для контента
- [ ] Создать базовые языковые файлы

#### Задача 4.2: Контент разделов "Введение"
- [ ] `introduction/overview.json` - обзор программы
- [ ] `introduction/installation.json` - установка и настройка
- [ ] `introduction/quick_start.json` - быстрый старт

#### Задача 4.3: Контент разделов "Управление данными"
- [ ] `data_management/file_loading.json` - загрузка файлов
- [ ] `data_management/data_preprocessing.json` - предобработка данных
- [ ] `data_management/file_operations.json` - операции с файлами

#### Задача 4.4: Контент разделов "Анализ"
- [ ] `analysis/deconvolution.json` - деконволюция пиков
- [ ] `analysis/model_fit.json` - Model-Fit анализ
- [ ] `analysis/model_free.json` - Model-Free анализ
- [ ] `analysis/model_based.json` - Model-Based анализ

#### Задача 4.5: Продвинутые разделы
- [ ] `advanced/series_analysis.json` - анализ серий
- [ ] `advanced/export_import.json` - экспорт/импорт
- [ ] `advanced/troubleshooting.json` - решение проблем

#### Задача 4.6: Мультиязычность
- [ ] Перевод всех разделов на английский язык
- [ ] Создание файлов `lang/ru.json` и `lang/en.json`
- [ ] Валидация переводов

#### Задача 4.7: Дополнительные темы
- [ ] `themes/academic.json` - академическая тема
- [ ] `themes/presentation.json` - презентационная тема

## 🎯 Критерии приемки

### 4.6 Функциональные требования
- ✅ Все разделы имеют контент на русском языке
- ✅ Критические разделы переведены на английский
- ✅ Навигационная структура соответствует схеме
- ✅ Контент корректно отображается в UI
- ✅ Поиск работает по всем разделам

### 4.7 Технические требования
- ✅ Все JSON файлы валидны
- ✅ Соответствие схемам данных
- ✅ Корректная работа ContentManager
- ✅ Интеграция с существующими компонентами
- ✅ Производительность загрузки данных

## 📊 Ожидаемые результаты

### 4.8 Deliverables
1. **Полная структура данных** - все директории и файлы созданы
2. **Контент 15+ разделов** - покрытие всех основных функций программы
3. **Мультиязычная поддержка** - русский + английский языки
4. **Интеграционные тесты** - проверка работы с UI компонентами
5. **Документация структуры данных** - схемы и примеры

### 4.9 Метрики качества
- **Покрытие функциональности**: 100% основных функций программы
- **Языковое покрытие**: 100% русский, 80%+ английский
- **Валидность JSON**: 100% файлов проходят валидацию
- **Производительность**: загрузка любого раздела < 100ms

## 🚀 Следующие шаги

### После завершения Фазы 4:
- **Фаза 5**: Integration Layer - интеграция с основным приложением
- **Фаза 6**: Testing & Polish - комплексное тестирование и доводка
- **Фаза 7**: Documentation - финальная документация

---

## 📅 Планируемые сроки
- **Старт**: Июнь 2025
- **Завершение**: Июнь 2025  
- **Продолжительность**: 1-2 дня активной работы

## 👥 Ответственность
- **Архитектура данных**: GitHub Copilot
- **Контент разделов**: GitHub Copilot + User
- **Переводы**: GitHub Copilot
- **Валидация**: Автоматизированные тесты
