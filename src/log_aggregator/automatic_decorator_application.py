"""
Automatic decorator application system for Stage 6 implementation.

This module implements automatic application of the @operation decorator to all
methods in BaseSlots classes that correspond to OperationType operations, eliminating
the need for manual decoration.
"""

from typing import Any, Dict, List, Set, Type

from src.core.app_settings import OperationType
from src.core.logger_config import logger

from .operation_decorator import operation


class AutomaticDecoratorApplicator:
    """
    System for automatically applying @operation decorators to BaseSlots classes.

    This class analyzes all BaseSlots subclasses and automatically applies
    operation decorators to methods that correspond to OperationType operations.
    """

    def __init__(self):
        self.operation_method_mapping = self._build_operation_method_mapping()
        self.decorated_classes: Set[str] = set()
        self.decoration_summary: Dict[str, List[str]] = {}

    def _build_operation_method_mapping(self) -> Dict[OperationType, List[str]]:
        """Build mapping between OperationType operations and their corresponding method names."""
        mapping = {
            # Basic data operations
            OperationType.ADD_REACTION: ["add_reaction", "create_reaction"],
            OperationType.REMOVE_REACTION: ["remove_reaction", "delete_reaction"],
            OperationType.HIGHLIGHT_REACTION: ["highlight_reaction"],
            OperationType.UPDATE_VALUE: ["update_value"],
            OperationType.DECONVOLUTION: ["deconvolution", "run_deconvolution"],
            OperationType.UPDATE_REACTIONS_PARAMS: ["update_reactions_params"],
            # File operations
            OperationType.LOAD_FILE: ["load_file", "import_file"],
            OperationType.RESET_FILE_DATA: ["reset_file_data", "reset_data"],
            OperationType.IMPORT_REACTIONS: ["import_reactions"],
            OperationType.EXPORT_REACTIONS: ["export_reactions"],
            OperationType.TO_A_T: ["to_a_t", "differential"],
            OperationType.TO_DTG: ["to_dtg"],
            OperationType.CHECK_OPERATION: ["check_operation", "check_differential"],
            OperationType.GET_DF_DATA: ["get_df_data"],
            OperationType.GET_ALL_DATA: ["get_all_data"],
            # Data access operations
            OperationType.GET_VALUE: ["get_value"],
            OperationType.SET_VALUE: ["set_value"],
            OperationType.REMOVE_VALUE: ["remove_value"],
            OperationType.GET_FULL_DATA: ["get_full_data"],
            # Series operations
            OperationType.ADD_NEW_SERIES: ["add_new_series", "add_series"],
            OperationType.DELETE_SERIES: ["delete_series", "remove_series"],
            OperationType.UPDATE_SERIES: ["update_series"],
            OperationType.GET_ALL_SERIES: ["get_all_series"],
            OperationType.GET_SERIES: ["get_series"],
            OperationType.RENAME_SERIES: ["rename_series"],
            OperationType.GET_SERIES_VALUE: ["get_series_value"],
            OperationType.SCHEME_CHANGE: ["scheme_change"],
            OperationType.MODEL_PARAMS_CHANGE: ["model_params_change"],
            OperationType.SELECT_SERIES: ["select_series"],
            OperationType.LOAD_DECONVOLUTION_RESULTS: ["load_deconvolution_results"],
            # Calculation operations
            OperationType.MODEL_BASED_CALCULATION: ["model_based_calculation"],
            OperationType.MODEL_FIT_CALCULATION: ["model_fit_calculation"],
            OperationType.MODEL_FREE_CALCULATION: ["model_free_calculation"],
            OperationType.GET_MODEL_FIT_REACTION_DF: ["get_model_fit_reaction_df"],
            OperationType.GET_MODEL_FREE_REACTION_DF: ["get_model_free_reaction_df"],
            OperationType.PLOT_MODEL_FIT_RESULT: ["plot_model_fit_result"],
            OperationType.PLOT_MODEL_FREE_RESULT: ["plot_model_free_result"],
            OperationType.UPDATE_MODEL_BASED_BEST_VALUES: ["update_model_based_best_values"],
            # Control operations
            OperationType.STOP_CALCULATION: ["stop_calculation"],
            OperationType.CALCULATION_FINISHED: ["calculation_finished"],
            # Other operations
            OperationType.GET_FILE_NAME: ["get_file_name"],
            OperationType.PLOT_DF: ["plot_df"],
            OperationType.PLOT_MSE_LINE: ["plot_mse_line"],
        }

        logger.debug(f"Built operation-method mapping for {len(mapping)} operations")
        return mapping

    def apply_automatic_decoration(self) -> Dict[str, List[str]]:
        """Apply automatic decoration to all eligible BaseSlots classes."""
        try:
            from src.core.base_signals import BaseSlots

            # Force import of all core modules to ensure subclasses are registered
            self._import_core_modules()

            # Get all BaseSlots subclasses
            baseslots_subclasses = self._get_all_baseslots_subclasses(BaseSlots)

            logger.info(f"Found {len(baseslots_subclasses)} BaseSlots subclasses for decoration")

            for cls in baseslots_subclasses:
                decorated_methods = self._decorate_class_methods(cls)
                if decorated_methods:
                    self.decoration_summary[cls.__name__] = decorated_methods
                    self.decorated_classes.add(cls.__name__)

            logger.info(f"Completed automatic decoration for {len(self.decorated_classes)} classes")
            return self.decoration_summary

        except ImportError as e:
            logger.error(f"Cannot apply automatic decoration: BaseSlots not available - {e}")
            return {}

    def _import_core_modules(self):
        """Import all core modules to ensure BaseSlots subclasses are loaded."""
        core_modules = [
            "src.core.calculation",
            "src.core.calculation_data",
            "src.core.calculation_data_operations",
            "src.core.file_data",
            "src.core.file_operations",
            "src.core.model_fit_calculation",
            "src.core.model_free_calculation",
            "src.core.series_data",
        ]

        for module_name in core_modules:
            try:
                __import__(module_name)
                logger.debug(f"Imported {module_name}")
            except ImportError as e:
                logger.warning(f"Could not import {module_name}: {e}")

    def _get_all_baseslots_subclasses(self, base_class: Type) -> Set[Type]:
        """Recursively get all subclasses of BaseSlots."""
        subclasses = set()

        for subclass in base_class.__subclasses__():
            # Skip the base class itself
            if subclass.__name__ != "BaseSlots":
                subclasses.add(subclass)
                # Recursively get subclasses
                subclasses.update(self._get_all_baseslots_subclasses(subclass))

        return subclasses

    def _decorate_class_methods(self, cls: Type) -> List[str]:
        """Decorate all eligible methods in a class."""
        decorated_methods = []

        # Always try to decorate process_request
        if hasattr(cls, "process_request"):
            if not hasattr(cls.process_request, "_is_operation_decorated"):
                try:
                    # Apply operation decorator to process_request
                    decorated_method = operation("PROCESS_REQUEST")(cls.process_request)
                    setattr(cls, "process_request", decorated_method)
                    decorated_methods.append("process_request")
                    logger.debug(f"Decorated process_request in {cls.__name__}")
                except Exception as e:
                    logger.warning(f"Failed to decorate process_request in {cls.__name__}: {e}")

        # Look for methods matching operation names
        for operation_type, method_names in self.operation_method_mapping.items():
            for method_name in method_names:
                if hasattr(cls, method_name):
                    method = getattr(cls, method_name)
                    if callable(method) and not hasattr(method, "_is_operation_decorated"):
                        try:
                            # Apply operation decorator
                            decorated_method = operation(operation_type.value)(method)
                            setattr(cls, method_name, decorated_method)
                            decorated_methods.append(method_name)
                            logger.debug(f"Decorated {method_name} in {cls.__name__} for {operation_type.value}")
                        except Exception as e:
                            logger.warning(f"Failed to decorate {method_name} in {cls.__name__}: {e}")

        return decorated_methods

    def validate_decorations(self) -> Dict[str, Any]:
        """Validate that decorations were applied correctly."""
        validation_results = {
            "total_classes": len(self.decorated_classes),
            "total_methods": sum(len(methods) for methods in self.decoration_summary.values()),
            "classes_with_issues": [],
            "missing_operations": [],
            "validation_passed": True,
        }

        # Check for missing critical operations
        critical_operations = [
            OperationType.LOAD_FILE,
            OperationType.GET_VALUE,
            OperationType.SET_VALUE,
            OperationType.DECONVOLUTION,
        ]

        for critical_op in critical_operations:
            found = False
            for method_names in self.operation_method_mapping[critical_op]:
                if any(
                    method_name in methods
                    for methods in self.decoration_summary.values()
                    for method_name in method_names
                ):
                    found = True
                    break
            if not found:
                validation_results["missing_operations"].append(critical_op.value)
                validation_results["validation_passed"] = False

        return validation_results

    def generate_report(self) -> str:
        """Generate a comprehensive report of the decoration process."""
        report = "=" * 60 + "\n"
        report += "AUTOMATIC DECORATOR APPLICATION REPORT\n"
        report += "=" * 60 + "\n"
        report += f"Total classes processed: {len(self.decorated_classes)}\n"
        report += f"Total operations mapped: {len(self.operation_method_mapping)}\n\n"

        report += "DECORATED CLASSES AND METHODS:\n"
        report += "-" * 40 + "\n"

        for class_name, methods in self.decoration_summary.items():
            report += f"📋 {class_name}: {len(methods)} methods\n"
            for method in methods:
                report += f"  ✅ {method}\n"
            report += "\n"

        # Add validation results
        validation = self.validate_decorations()
        if validation["validation_passed"]:
            report += "✅ All validations passed!\n"
        else:
            report += "❌ Validation issues found:\n"
            if validation["missing_operations"]:
                report += f"  Missing operations: {validation['missing_operations']}\n"

        report += "=" * 60
        return report


class AutoDecorationConfig:
    """Configuration for automatic decoration behavior."""

    ENABLED = True
    VALIDATE_DECORATIONS = True
    LOG_DECORATION_PROCESS = True
    REPORT_SUMMARY = True


def apply_automatic_decorators() -> Dict[str, List[str]]:
    """Main entry point for applying automatic decorators."""
    if not AutoDecorationConfig.ENABLED:
        logger.info("Automatic decoration is disabled")
        return {}

    logger.info("Starting automatic decorator application...")
    applicator = AutomaticDecoratorApplicator()
    decoration_summary = applicator.apply_automatic_decoration()

    if AutoDecorationConfig.VALIDATE_DECORATIONS:
        validation_results = applicator.validate_decorations()
        logger.info(f"Validation: {validation_results['validation_passed']}")

    if AutoDecorationConfig.REPORT_SUMMARY:
        report = applicator.generate_report()
        logger.info("Decoration Report:\n" + report)

    logger.info("Automatic decorator application completed successfully")
    return decoration_summary


def get_decoration_status(cls: Type, method_name: str) -> Dict[str, Any]:
    """Get detailed decoration status for a specific method."""
    if not hasattr(cls, method_name):
        return {"exists": False}

    method = getattr(cls, method_name)
    return {
        "exists": True,
        "is_decorated": getattr(method, "_is_operation_decorated", False),
        "operation_name": getattr(method, "_operation_name", None),
        "original_function": getattr(method, "_original_function", None),
        "is_callable": callable(method),
        "has_pyqt_signature": hasattr(method, "__pyqtSignature__"),
    }
