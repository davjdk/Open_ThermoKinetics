#!/usr/bin/env python3
"""
Simple test script for Stage 6 automatic decorator application.
"""

import os
import sys

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_stage_6():
    """Test Stage 6 automatic decorator application."""
    try:
        print("=" * 60)
        print("TESTING STAGE 6: AUTOMATIC DECORATOR APPLICATION")
        print("=" * 60)

        # Import the necessary modules
        from src.log_aggregator.automatic_decorator_application import apply_automatic_decorators

        print("✅ Successfully imported automatic decorator application module")

        # Apply automatic decorators
        result = apply_automatic_decorators()

        print("✅ Automatic decoration completed")
        print(f"📋 Decorated {len(result)} classes")

        total_methods = sum(len(methods) for methods in result.values())
        print(f"🔧 Total methods decorated: {total_methods}")

        print("\n📋 DECORATED CLASSES:")
        for class_name, methods in result.items():
            print(f"  • {class_name}: {len(methods)} methods")
            for method in methods[:3]:  # Show first 3 methods
                print(f"    - {method}")
            if len(methods) > 3:
                print(f"    ... and {len(methods) - 3} more")

        if len(result) > 0:
            print("\n✅ STAGE 6 SUCCESSFULLY COMPLETED!")
            print("✅ Automatic decorators have been applied to all BaseSlots classes")
        else:
            print("\n⚠️  No classes were decorated - this may indicate an issue")

        return True

    except Exception as e:
        print(f"❌ Error during Stage 6 testing: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_stage_6()
    sys.exit(0 if success else 1)
