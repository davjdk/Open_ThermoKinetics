"""
Анализ избыточных компонентов системы логирования
Этап 7: Выявление и удаление избыточных компонентов
"""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ComponentAnalysis:
    """Результат анализа компонента"""

    component_name: str
    file_path: str
    lines_of_code: int
    status: str  # "FULL_REMOVAL", "PARTIAL_REMOVAL", "SIMPLIFICATION", "KEEP"
    reason: str
    redundant_features: List[str]
    useful_features: List[str]
    code_reduction_percentage: int
    migration_required: bool = False
    migration_steps: List[str] = None

    def __post_init__(self):
        if self.migration_steps is None:
            self.migration_steps = []


class LegacyComponentAnalyzer:
    """Анализ устаревших компонентов системы логирования"""

    def __init__(self, log_aggregator_path: str = "src/log_aggregator"):
        self.log_aggregator_path = log_aggregator_path
        self.analysis_results: List[ComponentAnalysis] = []

    def analyze_all_components(self) -> List[ComponentAnalysis]:
        """Провести анализ всех компонентов"""

        # Анализ каждого компонента
        self.analysis_results = [
            self.analyze_value_aggregator(),
            self.analyze_pattern_detector(),
            self.analyze_operation_aggregator(),
            self.analyze_error_expansion(),
            self.analyze_performance_monitor(),
        ]

        return self.analysis_results

    def analyze_value_aggregator(self) -> ComponentAnalysis:
        """Анализ ValueAggregator - может быть полностью избыточным"""

        file_path = os.path.join(self.log_aggregator_path, "value_aggregator.py")
        loc = self._count_lines_of_code(file_path)

        return ComponentAnalysis(
            component_name="ValueAggregator",
            file_path=file_path,
            lines_of_code=loc,
            status="FULL_REMOVAL",
            reason="Replaced by operation metrics system",
            redundant_features=[
                "Value aggregation logic",
                "Large data summarization",
                "Value compression algorithms",
                "Aggregation configuration",
            ],
            useful_features=[],
            code_reduction_percentage=100,
            migration_required=True,
            migration_steps=[
                "Move large data summarization to OperationMetrics",
                "Integrate value compression into operation_logger.add_metric()",
                "Update error contexts to use operation metrics instead",
                "Remove ValueAggregationConfig from global config",
            ],
        )

    def analyze_pattern_detector(self) -> ComponentAnalysis:
        """Анализ PatternDetector после внедрения явных операций"""

        file_path = os.path.join(self.log_aggregator_path, "pattern_detector.py")
        loc = self._count_lines_of_code(file_path)

        return ComponentAnalysis(
            component_name="PatternDetector",
            file_path=file_path,
            lines_of_code=loc,
            status="PARTIAL_REMOVAL",
            reason="Many patterns replaced by explicit operations",
            redundant_features=[
                "cascade_component_initialization",
                "request_response_cycle",
                "basic_similarity",
                "temporal_grouping",
                "operation_detection_algorithms",
            ],
            useful_features=["plot_lines_addition", "file_operations", "gui_updates", "error_pattern_detection"],
            code_reduction_percentage=40,
            migration_required=False,
        )

    def analyze_operation_aggregator(self) -> ComponentAnalysis:
        """Анализ OperationAggregator - убрать автоматический режим"""

        file_path = os.path.join(self.log_aggregator_path, "operation_aggregator.py")
        loc = self._count_lines_of_code(file_path)

        return ComponentAnalysis(
            component_name="OperationAggregator",
            file_path=file_path,
            lines_of_code=loc,
            status="SIMPLIFICATION",
            reason="Remove automatic mode, keep only explicit operations",
            redundant_features=[
                "Automatic cascade detection",
                "Pattern-based operation grouping",
                "Time-window based aggregation",
                "Root operation detection",
                "cascade_window logic",
                "min_cascade_size",
                "automatic pattern grouping",
            ],
            useful_features=[
                "Explicit operation mode",
                "Operation metrics collection",
                "Manual operation boundaries",
                "Integration with OperationMonitor",
            ],
            code_reduction_percentage=45,
            migration_required=False,
        )

    def analyze_error_expansion(self) -> ComponentAnalysis:
        """Анализ ErrorExpansionEngine - может быть упрощен"""

        file_path = os.path.join(self.log_aggregator_path, "error_expansion.py")
        loc = self._count_lines_of_code(file_path)

        return ComponentAnalysis(
            component_name="ErrorExpansionEngine",
            file_path=file_path,
            lines_of_code=loc,
            status="PARTIAL_REMOVAL",
            reason="Some functions duplicate operation metrics",
            redundant_features=[
                "operation_trace_analysis",
                "context_window_analysis",
                "automated_pattern_matching",
                "operation_correlation_analysis",
            ],
            useful_features=[
                "error_classification",
                "actionable_recommendations",
                "stack_trace_analysis",
                "error_context_extraction",
            ],
            code_reduction_percentage=30,
            migration_required=False,
        )

    def analyze_performance_monitor(self) -> ComponentAnalysis:
        """Анализ PerformanceMonitor - частичное дублирование с OperationMonitor"""

        file_path = os.path.join(self.log_aggregator_path, "performance_monitor.py")
        loc = self._count_lines_of_code(file_path)

        return ComponentAnalysis(
            component_name="PerformanceMonitor",
            file_path=file_path,
            lines_of_code=loc,
            status="SIMPLIFICATION",
            reason="Remove overlap with OperationMonitor, focus on system metrics",
            redundant_features=[
                "operation_latency_tracking",
                "request_count_monitoring",
                "component_interaction_tracking",
            ],
            useful_features=[
                "system_resource_monitoring",
                "global_performance_metrics",
                "bottleneck_detection",
                "memory_usage_tracking",
            ],
            code_reduction_percentage=25,
            migration_required=False,
        )

    def _count_lines_of_code(self, file_path: str) -> int:
        """Подсчитать строки кода в файле"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Исключить пустые строки и комментарии
                code_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
                return len(code_lines)
        except FileNotFoundError:
            return 0

    def generate_simplification_report(self) -> Dict:
        """Сгенерировать отчет об упрощении системы"""

        if not self.analysis_results:
            self.analyze_all_components()

        removed_components = [comp for comp in self.analysis_results if comp.status == "FULL_REMOVAL"]

        simplified_components = [
            comp for comp in self.analysis_results if comp.status in ["PARTIAL_REMOVAL", "SIMPLIFICATION"]
        ]

        total_lines_before = sum(comp.lines_of_code for comp in self.analysis_results)
        total_lines_removed = sum(
            comp.lines_of_code * comp.code_reduction_percentage // 100 for comp in self.analysis_results
        )

        return {
            "removed_components": [
                {"name": comp.component_name, "loc_removed": comp.lines_of_code, "functionality": comp.reason}
                for comp in removed_components
            ],
            "simplified_components": [
                {
                    "name": comp.component_name,
                    "loc_before": comp.lines_of_code,
                    "loc_after": comp.lines_of_code * (100 - comp.code_reduction_percentage) // 100,
                    "reduction": f"{comp.code_reduction_percentage}%",
                }
                for comp in simplified_components
            ],
            "total_code_reduction": {
                "lines_removed": total_lines_removed,
                "lines_before": total_lines_before,
                "lines_after": total_lines_before - total_lines_removed,
                "percentage": f"{total_lines_removed * 100 // total_lines_before}%" if total_lines_before > 0 else "0%",
                "maintainability_improvement": "High",
            },
            "migration_requirements": [
                {"component": comp.component_name, "steps": comp.migration_steps}
                for comp in self.analysis_results
                if comp.migration_required
            ],
        }

    def get_refactoring_priority(self) -> List[ComponentAnalysis]:
        """Получить компоненты в порядке приоритета рефакторинга"""

        if not self.analysis_results:
            self.analyze_all_components()

        # Сортировать по статусу и проценту упрощения
        priority_order = {"FULL_REMOVAL": 1, "PARTIAL_REMOVAL": 2, "SIMPLIFICATION": 3, "KEEP": 4}

        return sorted(
            self.analysis_results,
            key=lambda comp: (priority_order.get(comp.status, 5), -comp.code_reduction_percentage),
        )


class ComponentRefactoringPlan:
    """План рефакторинга устаревших компонентов"""

    def __init__(self, analyzer: LegacyComponentAnalyzer):
        self.analyzer = analyzer

    def create_refactoring_steps(self) -> List[Dict]:
        """Создать детальный план рефакторинга"""

        priority_components = self.analyzer.get_refactoring_priority()
        refactoring_steps = []

        for comp in priority_components:
            if comp.status == "FULL_REMOVAL":
                refactoring_steps.append(self._create_removal_plan(comp))
            elif comp.status in ["PARTIAL_REMOVAL", "SIMPLIFICATION"]:
                refactoring_steps.append(self._create_simplification_plan(comp))

        return refactoring_steps

    def _create_removal_plan(self, comp: ComponentAnalysis) -> Dict:
        """Создать план полного удаления компонента"""

        return {
            "component": comp.component_name,
            "action": "FULL_REMOVAL",
            "file_path": comp.file_path,
            "backup_required": True,
            "migration_steps": comp.migration_steps,
            "verification_steps": [
                f"Ensure no imports of {comp.component_name}",
                "Run full test suite",
                "Verify functionality preservation",
                "Check for performance regressions",
            ],
            "rollback_plan": f"Restore {comp.file_path} from backup",
        }

    def _create_simplification_plan(self, comp: ComponentAnalysis) -> Dict:
        """Создать план упрощения компонента"""

        return {
            "component": comp.component_name,
            "action": "SIMPLIFICATION",
            "file_path": comp.file_path,
            "features_to_remove": comp.redundant_features,
            "features_to_keep": comp.useful_features,
            "expected_reduction": f"{comp.code_reduction_percentage}%",
            "refactoring_steps": [
                f"Backup original {comp.file_path}",
                f"Remove redundant features: {', '.join(comp.redundant_features[:3])}...",
                f"Preserve essential features: {', '.join(comp.useful_features[:3])}...",
                "Update imports and dependencies",
                "Run targeted tests",
                "Performance validation",
            ],
            "verification_steps": [
                "Verify essential functionality preserved",
                "Run performance benchmarks",
                "Check integration points",
                "Validate test coverage",
            ],
        }


def analyze_system_redundancy():
    """Главная функция анализа избыточности системы"""

    analyzer = LegacyComponentAnalyzer()
    analyzer.analyze_all_components()

    # Сгенерировать отчет
    report = analyzer.generate_simplification_report()

    print("=== Анализ избыточности системы логирования ===")
    print(f"Общее сокращение кода: {report['total_code_reduction']['percentage']}")
    print(f"Строк удалено: {report['total_code_reduction']['lines_removed']}")

    print("\n--- Компоненты для полного удаления ---")
    for comp in report["removed_components"]:
        print(f"• {comp['name']}: {comp['loc_removed']} строк")
        print(f"  Причина: {comp['functionality']}")

    print("\n--- Компоненты для упрощения ---")
    for comp in report["simplified_components"]:
        print(f"• {comp['name']}: {comp['loc_before']} → {comp['loc_after']} строк (-{comp['reduction']})")

    # Создать план рефакторинга
    planner = ComponentRefactoringPlan(analyzer)
    refactoring_steps = planner.create_refactoring_steps()

    print("\n--- План рефакторинга ---")
    for i, step in enumerate(refactoring_steps, 1):
        print(f"{i}. {step['component']}: {step['action']}")

    return analyzer, report, refactoring_steps


if __name__ == "__main__":
    analyze_system_redundancy()


class TestComponentAnalysis:
    """Тесты анализа компонентов системы логирования"""

    def test_value_aggregator_redundancy(self):
        """Проверить анализ избыточности ValueAggregator"""
        analyzer = LegacyComponentAnalyzer()
        analysis = analyzer.analyze_value_aggregator()

        assert analysis.component_name == "ValueAggregator"
        assert analysis.status == "FULL_REMOVAL"
        assert analysis.code_reduction_percentage == 100
        assert analysis.migration_required is True
        assert "operation metrics" in analysis.reason.lower()

    def test_pattern_detector_optimization(self):
        """Проверить анализ оптимизации PatternDetector"""
        analyzer = LegacyComponentAnalyzer()
        analysis = analyzer.analyze_pattern_detector()

        assert analysis.component_name == "PatternDetector"
        assert analysis.status == "PARTIAL_REMOVAL"
        assert analysis.code_reduction_percentage > 0
        assert "replaced by explicit operations" in analysis.reason

    def test_system_wide_analysis(self):
        """Проверить системный анализ всех компонентов"""
        analyzer = LegacyComponentAnalyzer()
        results = analyzer.analyze_all_components()

        assert len(results) == 5

        # Найти ValueAggregator в результатах
        value_agg_analysis = next((r for r in results if r.component_name == "ValueAggregator"), None)
        assert value_agg_analysis is not None
        assert value_agg_analysis.status == "FULL_REMOVAL"

    def test_refactoring_plan_generation(self):
        """Проверить генерацию плана рефакторинга"""
        analyzer = LegacyComponentAnalyzer()
        analyzer.analyze_all_components()

        planner = ComponentRefactoringPlan(analyzer)
        steps = planner.create_refactoring_steps()

        assert len(steps) > 0

        # Проверить, что ValueAggregator стоит первым в плане удаления
        removal_steps = [s for s in steps if s["action"] == "FULL_REMOVAL"]
        assert len(removal_steps) >= 1


class TestLegacyComponentAnalyzer:
    """Тесты класса анализатора компонентов"""

    def test_analyzer_initialization(self):
        """Проверить инициализацию анализатора"""
        analyzer = LegacyComponentAnalyzer()
        assert analyzer.log_aggregator_path == "src/log_aggregator"
        assert len(analyzer.analysis_results) == 0

    def test_component_file_exists(self):
        """Проверить наличие файлов компонентов для анализа"""
        analyzer = LegacyComponentAnalyzer()

        # ValueAggregator должен быть удален, поэтому файла не должно быть
        value_agg_path = os.path.join(analyzer.log_aggregator_path, "value_aggregator.py")
        assert not os.path.exists(value_agg_path), "ValueAggregator должен быть удален"

        # Остальные компоненты должны существовать
        pattern_path = os.path.join(analyzer.log_aggregator_path, "pattern_detector.py")
        assert os.path.exists(pattern_path), "PatternDetector должен существовать"


class TestComponentRefactoringPlan:
    """Тесты плана рефакторинга компонентов"""

    def test_plan_prioritization(self):
        """Проверить приоритизацию в плане рефакторинга"""
        analyzer = LegacyComponentAnalyzer()
        analyzer.analyze_all_components()

        planner = ComponentRefactoringPlan(analyzer)
        steps = planner.create_refactoring_steps()

        # Полное удаление должно быть первым приоритетом
        priority_order = [s["action"] for s in steps]
        full_removal_index = priority_order.index("FULL_REMOVAL") if "FULL_REMOVAL" in priority_order else -1
        simplify_index = priority_order.index("SIMPLIFICATION") if "SIMPLIFICATION" in priority_order else -1

        if full_removal_index >= 0 and simplify_index >= 0:
            assert full_removal_index < simplify_index, "FULL_REMOVAL должен идти перед SIMPLIFICATION"
