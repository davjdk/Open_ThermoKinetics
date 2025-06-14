"""
Metaclass for automatic operation decoration of BaseSlots classes.

This module provides a metaclass that automatically applies operation decorators
to process_request methods in BaseSlots subclasses, enabling seamless integration
of operation logging without manual decoration.
"""

from typing import Any, Dict, Type

from src.core.logger_config import logger

from .operation_decorator import operation


class AutoOperationMeta(type):
    """
    Metaclass for automatic operation decoration of BaseSlots classes.

    This metaclass automatically decorates process_request methods in BaseSlots
    subclasses with the @operation decorator, enabling automatic operation logging
    without requiring manual decoration of each method.

    The metaclass:
    - Detects BaseSlots subclasses
    - Automatically decorates process_request methods
    - Preserves original method signatures and metadata
    - Provides operation type auto-detection
    - Logs decoration activity for debugging
    """

    def __new__(mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs) -> Type:
        """
        Create a new class with automatic operation decoration.

        Args:
            name: Name of the class being created
            bases: Base classes
            namespace: Class namespace with methods and attributes
            **kwargs: Additional keyword arguments

        Returns:
            New class with decorated methods
        """
        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Only process BaseSlots subclasses
        if mcs._is_baseslots_subclass(cls):
            mcs._auto_decorate_process_request(cls)

        return cls

    @staticmethod
    def _is_baseslots_subclass(cls: Type) -> bool:
        """
        Check if a class is a subclass of BaseSlots.

        Args:
            cls: Class to check

        Returns:
            True if class is BaseSlots subclass
        """
        try:
            # Import BaseSlots to check inheritance
            from src.core.base_signals import BaseSlots

            return issubclass(cls, BaseSlots) and cls.__name__ != "BaseSlots"
        except ImportError:
            # BaseSlots not available, skip auto-decoration
            logger.warning("BaseSlots not available for auto-decoration")
            return False

    @staticmethod
    def _auto_decorate_process_request(cls: Type) -> None:
        """
        Automatically decorate process_request method if present.

        Args:
            cls: Class to process
        """
        # Check if process_request method exists
        if hasattr(cls, "process_request") and callable(getattr(cls, "process_request")):
            original_method = getattr(cls, "process_request")

            # Only decorate if not already decorated
            if not getattr(original_method, "_is_operation_decorated", False):
                # Apply operation decorator with auto-detection
                decorated_method = operation(auto_detect=True, handle_exceptions=True)(original_method)
                setattr(cls, "process_request", decorated_method)

                logger.debug(f"Auto-decorated process_request method in {cls.__name__}")
            else:
                logger.debug(f"process_request method in {cls.__name__} already decorated")


def apply_auto_decoration_to_existing_classes():
    """
    Apply automatic decoration to existing BaseSlots classes.

    This function can be called to retroactively apply operation decorators
    to BaseSlots classes that were already defined before the metaclass
    was introduced.
    """
    try:
        from src.core.base_signals import BaseSlots

        # Get all subclasses of BaseSlots
        def get_all_subclasses(cls):
            """Recursively get all subclasses."""
            subclasses = set()
            for subclass in cls.__subclasses__():
                subclasses.add(subclass)
                subclasses.update(get_all_subclasses(subclass))
            return subclasses

        baseslots_subclasses = get_all_subclasses(BaseSlots)

        for subclass in baseslots_subclasses:
            AutoOperationMeta._auto_decorate_process_request(subclass)

        logger.info(f"Applied auto-decoration to {len(baseslots_subclasses)} BaseSlots subclasses")

    except ImportError:
        logger.warning("Cannot apply auto-decoration: BaseSlots not available")


class OperationAwareMixin:
    """
    Mixin class that can be used with existing BaseSlots classes.

    This mixin provides operation-aware functionality without requiring
    metaclass usage. It can be mixed into existing BaseSlots subclasses
    to enable automatic operation decoration.

    Usage:
        class MyDataOperations(OperationAwareMixin, BaseSlots):
            def process_request(self, params):
                # This method will be automatically decorated
                pass
    """

    def __init_subclass__(cls, **kwargs):
        """
        Called when a class is subclassed.

        Automatically applies operation decoration to process_request methods.
        """
        super().__init_subclass__(**kwargs)

        # Apply auto-decoration
        AutoOperationMeta._auto_decorate_process_request(cls)


# Factory function for creating operation-aware BaseSlots classes
def create_operation_aware_class(base_class: Type, class_name: str) -> Type:
    """
    Factory function to create operation-aware versions of BaseSlots classes.

    Args:
        base_class: Base class to extend (should be BaseSlots subclass)
        class_name: Name for the new class

    Returns:
        New class with automatic operation decoration

    Usage:
        OperationAwareFileData = create_operation_aware_class(FileData, "OperationAwareFileData")
    """
    # Create new class with metaclass
    return AutoOperationMeta(
        class_name,
        (base_class,),
        {
            "__module__": base_class.__module__,
            "__doc__": f"Operation-aware version of {base_class.__name__}",
        },
    )


# Decorator for manual application to specific classes
def operation_aware_class(cls: Type) -> Type:
    """
    Class decorator for enabling operation awareness on BaseSlots classes.

    This decorator can be applied to existing BaseSlots subclasses to enable
    automatic operation decoration without using the metaclass.

    Args:
        cls: Class to make operation-aware

    Returns:
        Modified class with automatic operation decoration

    Usage:
        @operation_aware_class
        class MyDataOperations(BaseSlots):
            def process_request(self, params):
                # This method will be automatically decorated
                pass
    """
    AutoOperationMeta._auto_decorate_process_request(cls)
    return cls
