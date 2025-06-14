"""
Tabular formatter for operation results using tabulate library.

This module provides explicit-mode tabular formatting for operation results
with clean ASCII output that is readable both in console and log files.
Uses the tabulate library for consistent, human-readable table formatting.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from tabulate import tabulate

    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

logger = logging.getLogger(__name__)


class TabularFormatter:
    """
    Explicit-mode tabular formatter using tabulate library for clean ASCII output.

    This class provides methods to format operation results and data into
    well-formatted ASCII tables that are readable both in console and log files.
    """

    def __init__(self, table_format: str = "grid"):
        """
        Initialize the TabularFormatter.

        Args:
            table_format: Tabulate table format ('grid', 'simple', 'plain', 'pipe', 'fancy_grid', etc.)
                         See tabulate documentation for all available formats.
        """
        if not TABULATE_AVAILABLE:
            logger.warning("tabulate library not available. Falling back to simple formatting.")
            self.tabulate_enabled = False
        else:
            self.tabulate_enabled = True

        self.table_format = table_format

        # Available table formats with descriptions
        self.available_formats = {
            "grid": "Grid format with borders",
            "simple": "Simple format without borders",
            "plain": "Plain format, minimal styling",
            "pipe": "Pipe-separated format (Markdown compatible)",
            "fancy_grid": "Fancy grid with double lines",
            "github": "GitHub-flavored Markdown",
            "html": "HTML table format",
            "latex": "LaTeX table format",
        }

    def format_operation_results(
        self,
        results: List[Dict[str, Any]],
        title: Optional[str] = None,
        columns: Optional[List[str]] = None,
        table_format_override: Optional[str] = None,
    ) -> str:
        """
        Format operation results into a table.

        Args:
            results: List of dictionaries containing operation data
            title: Optional table title
            columns: Optional list of column names to include
            table_format_override: Override default table format for this table

        Returns:
            Formatted table as string
        """
        if not results:
            return "No results to display."

        # Determine columns
        if columns is None:
            # Use all unique keys from all results
            all_keys = set()
            for result in results:
                all_keys.update(result.keys())
            columns = sorted(all_keys)

        if self.tabulate_enabled:
            return self._format_tabulate_table(results, title, columns, table_format_override)
        else:
            return self._format_fallback_table(results, title, columns)

    def format_summary_table(
        self, summary_data: Dict[str, Any], title: Optional[str] = None, table_format_override: Optional[str] = None
    ) -> str:
        """
        Format summary data into a two-column table (key-value pairs).

        Args:
            summary_data: Dictionary of summary data
            title: Optional table title
            table_format_override: Override default table format for this table

        Returns:
            Formatted table as string
        """
        if not summary_data:
            return "No summary data to display."

        # Convert to list of dicts for consistent formatting
        results = [{"Property": key, "Value": str(value)} for key, value in summary_data.items()]

        return self.format_operation_results(
            results=results,
            title=title or "Summary",
            columns=["Property", "Value"],
            table_format_override=table_format_override,
        )

    def _format_tabulate_table(
        self,
        results: List[Dict[str, Any]],
        title: Optional[str],
        columns: List[str],
        table_format_override: Optional[str],
    ) -> str:
        """Format table using tabulate library."""

        # Prepare data for tabulate
        table_data = []
        for result in results:
            row = []
            for column in columns:
                value = result.get(column, "")
                # Format numbers for better readability
                if isinstance(value, (int, float)):
                    if isinstance(value, float):
                        formatted_value = f"{value:.4f}" if abs(value) < 1000 else f"{value:.2e}"
                    else:
                        formatted_value = str(value)
                else:
                    formatted_value = str(value)
                row.append(formatted_value)
            table_data.append(row)

        # Use specified format or default
        fmt = table_format_override or self.table_format

        # Generate table
        table_str = tabulate(table_data, headers=columns, tablefmt=fmt)

        # Add title if provided
        if title:
            title_line = f"\n{title}"
            separator = "=" * len(title)
            return f"{title_line}\n{separator}\n{table_str}\n"
        else:
            return f"{table_str}\n"

    def _format_fallback_table(self, results: List[Dict[str, Any]], title: Optional[str], columns: List[str]) -> str:
        """Fallback ASCII table formatting when tabulate is not available."""
        lines = []

        if title:
            lines.append(f"\n{title}")
            lines.append("=" * len(title))

        if not results:
            lines.append("No data to display.")
            return "\n".join(lines)

        # Calculate column widths
        col_widths = {}
        for col in columns:
            col_widths[col] = len(col)
            for result in results:
                value = str(result.get(col, ""))
                col_widths[col] = max(col_widths[col], len(value))

        # Create header
        header_parts = []
        separator_parts = []
        for col in columns:
            width = col_widths[col] + 2  # padding
            header_parts.append(f" {col:<{width-2}} ")
            separator_parts.append("-" * width)

        lines.append("|" + "|".join(header_parts) + "|")
        lines.append("|" + "|".join(separator_parts) + "|")

        # Add rows
        for result in results:
            row_parts = []
            for col in columns:
                value = str(result.get(col, ""))
                width = col_widths[col] + 2
                row_parts.append(f" {value:<{width-2}} ")
            lines.append("|" + "|".join(row_parts) + "|")

        return "\n".join(lines)

    def create_comparison_table(
        self,
        data_sets: Dict[str, List[Dict[str, Any]]],
        title: Optional[str] = None,
        table_format_override: Optional[str] = None,
    ) -> str:
        """
        Create a comparison table from multiple data sets.

        Args:
            data_sets: Dictionary where keys are dataset names and values are result lists
            title: Optional table title
            table_format_override: Override default table format for this table

        Returns:
            Formatted comparison table as string
        """
        if not data_sets:
            return "No data sets to compare."

        # Create comparison data
        comparison_data = []
        for dataset_name, results in data_sets.items():
            count = len(results)
            # Create a simple summary
            if results:
                keys = list(results[0].keys()) if results else []
                summary = f"Columns: {', '.join(keys[:3])}" + ("..." if len(keys) > 3 else "")
            else:
                summary = "No data"

            comparison_data.append({"Dataset": dataset_name, "Count": count, "Summary": summary})

        return self.format_operation_results(
            results=comparison_data,
            title=title or "Dataset Comparison",
            columns=["Dataset", "Count", "Summary"],
            table_format_override=table_format_override,
        )

    def set_table_format(self, table_format: str) -> None:
        """
        Set the default table format.

        Args:
            table_format: Format name (see available_formats for options)
        """
        if table_format in self.available_formats:
            self.table_format = table_format
        else:
            logger.warning(
                f"Unknown table format '{table_format}'. " f"Available formats: {list(self.available_formats.keys())}"
            )

    def get_available_formats(self) -> Dict[str, str]:
        """Get dictionary of available table formats with descriptions."""
        return self.available_formats.copy()

    def is_tabulate_available(self) -> bool:
        """Check if tabulate library is available."""
        return self.tabulate_enabled


# Example usage and testing functions
def demo_tables():
    """Demonstrate various table formatting options."""
    formatter = TabularFormatter()

    # Sample data
    sample_results = [
        {"Operation": "load_file", "Duration": 0.234, "Status": "Success", "Records": 1000},
        {"Operation": "process_data", "Duration": 1.567, "Status": "Success", "Records": 950},
        {"Operation": "save_results", "Duration": 0.089, "Status": "Success", "Records": 950},
        {"Operation": "validate", "Duration": 0.445, "Status": "Warning", "Records": 948},
    ]

    summary_data = {"Total Operations": 4, "Success Rate": "75%", "Average Duration": "0.584s", "Total Records": 3848}

    print("=== DEMO: Tabulate Table Formatting ===\n")
    print(f"Tabulate available: {formatter.is_tabulate_available()}")

    # Test different formats
    formats = ["grid", "simple", "plain", "pipe", "fancy_grid"]

    for fmt in formats:
        print(f"\n--- Format: {fmt} ---")
        table_output = formatter.format_operation_results(
            results=sample_results, title=f"Operation Results ({fmt} format)", table_format_override=fmt
        )
        print(table_output)

    # Test summary table
    print("\n--- Summary Table ---")
    summary_output = formatter.format_summary_table(summary_data=summary_data, title="Execution Summary")
    print(summary_output)

    # Test comparison table
    print("\n--- Comparison Table ---")
    comparison_data = {"Dataset A": sample_results[:2], "Dataset B": sample_results[2:], "Empty Set": []}
    comparison_output = formatter.create_comparison_table(data_sets=comparison_data, title="Dataset Comparison")
    print(comparison_output)


if __name__ == "__main__":
    demo_tables()
