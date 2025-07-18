"""Tests for the execution environment."""

import pytest
from unittest.mock import Mock, patch

from src.plaque.environment import Environment
from src.plaque.cell import Cell, CellType


class TestEnvironmentBasics:
    """Test basic environment functionality."""

    def test_environment_initialization(self):
        """Test environment initializes correctly."""
        env = Environment()
        assert env.locals == {"__name__": "__main__"}
        assert env.globals == env.locals  # globals and locals should be the same

    def test_simple_expression(self):
        """Test executing simple expression."""
        env = Environment()
        cell = Cell(CellType.CODE, "2 + 3", 1)

        result = env.execute_cell(cell)

        assert result == 5
        assert cell.result == 5
        assert cell.error is None

    def test_simple_assignment(self):
        """Test executing assignment statement."""
        env = Environment()
        cell = Cell(CellType.CODE, "x = 42", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is None
        assert env.locals.get("x") == 42

    def test_variable_persistence(self):
        """Test that variables persist between cell executions."""
        env = Environment()

        # First cell: define variable
        cell1 = Cell(CellType.CODE, "x = 10", 1)
        env.execute_cell(cell1)

        # Second cell: use variable
        cell2 = Cell(CellType.CODE, "y = x * 2", 2)
        env.execute_cell(cell2)

        # Third cell: return variable
        cell3 = Cell(CellType.CODE, "y", 3)
        result = env.execute_cell(cell3)

        assert result == 20
        assert env.locals.get("x") == 10
        assert env.locals.get("y") == 20

    def test_function_definition_and_call(self):
        """Test defining and calling functions."""
        env = Environment()

        # Define function
        cell1 = Cell(
            CellType.CODE,
            """
def square(n):
    return n * n
""",
            1,
        )
        env.execute_cell(cell1)

        # Call function
        cell2 = Cell(CellType.CODE, "square(5)", 2)
        result = env.execute_cell(cell2)

        assert result == 25
        assert callable(env.locals.get("square"))

    def test_multiple_statements_with_expression(self):
        """Test cell with multiple statements ending in expression."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
x = 5
y = 10
x + y
""",
            1,
        )

        result = env.execute_cell(cell)

        assert result == 15
        assert cell.result == 15
        assert env.locals.get("x") == 5
        assert env.locals.get("y") == 10

    def test_empty_cell(self):
        """Test executing empty cell."""
        env = Environment()
        cell = Cell(CellType.CODE, "", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is None

    def test_whitespace_only_cell(self):
        """Test executing cell with only whitespace."""
        env = Environment()
        cell = Cell(CellType.CODE, "   \n\t  \n  ", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is None


class TestErrorHandling:
    """Test error handling in environment."""

    def test_syntax_error(self):
        """Test syntax error handling."""
        env = Environment()
        cell = Cell(CellType.CODE, "if True\n    print('missing colon')", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is not None
        assert "SyntaxError" in cell.error
        assert "missing colon" in cell.error or "invalid syntax" in cell.error

    def test_runtime_error(self):
        """Test runtime error handling."""
        env = Environment()
        cell = Cell(CellType.CODE, "1 / 0", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is not None
        assert "ZeroDivisionError" in cell.error

    def test_name_error(self):
        """Test undefined variable error."""
        env = Environment()
        cell = Cell(CellType.CODE, "undefined_variable", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is not None
        assert "NameError" in cell.error
        assert "undefined_variable" in cell.error

    def test_import_error(self):
        """Test import error handling."""
        env = Environment()
        cell = Cell(CellType.CODE, "import nonexistent_module", 1)

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result is None
        assert cell.error is not None
        assert "ModuleNotFoundError" in cell.error or "ImportError" in cell.error

    def test_error_clears_previous_result(self):
        """Test that errors clear previous results."""
        env = Environment()

        # First cell: successful
        cell1 = Cell(CellType.CODE, "42", 1)
        env.execute_cell(cell1)
        assert cell1.result == 42
        assert cell1.error is None

        # Second cell: error
        cell1.content = "1 / 0"  # Reuse same cell object
        env.execute_cell(cell1)
        assert cell1.result is None
        assert cell1.error is not None


class TestSyntaxErrorFormatting:
    """Test syntax error formatting."""

    def test_syntax_error_with_context(self):
        """Test syntax error includes context lines."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
line1 = 1
if True
    line3 = 3
""",
            1,
        )

        env.execute_cell(cell)

        assert cell.error is not None
        assert "SyntaxError" in cell.error
        assert "Context:" in cell.error
        # Should show line numbers and highlight error line
        assert ">>>" in cell.error

    def test_syntax_error_pointer(self):
        """Test syntax error shows column pointer."""
        env = Environment()
        cell = Cell(CellType.CODE, "x = (1 + 2", 1)  # Missing closing paren

        env.execute_cell(cell)

        assert cell.error is not None
        assert "SyntaxError" in cell.error
        # Should include a pointer to the error location
        assert "^" in cell.error or "Context:" in cell.error


class TestRuntimeErrorFormatting:
    """Test runtime error formatting."""

    def test_runtime_error_traceback_cleaning(self):
        """Test that internal plaque frames are filtered from traceback."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
def problematic_function():
    return 1 / 0

problematic_function()
""",
            1,
        )

        env.execute_cell(cell)

        assert cell.error is not None
        assert "ZeroDivisionError" in cell.error
        # Should not contain plaque internal paths
        assert "plaque/" not in cell.error
        assert "environment.py" not in cell.error
        # Should contain line information about the cell
        assert "Line" in cell.error or "Traceback" in cell.error

    def test_runtime_error_with_line_numbers(self):
        """Test runtime error includes cell line numbers."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
x = 1
y = 2
z = x / (y - 2)  # This will cause ZeroDivisionError
""",
            1,
        )

        env.execute_cell(cell)

        assert cell.error is not None
        assert "ZeroDivisionError" in cell.error
        # Should reference the specific line in the cell
        assert "Line" in cell.error


class TestMatplotlibIntegration:
    """Test matplotlib figure capture."""

    @patch("src.plaque.environment.capture_matplotlib_plots")
    def test_matplotlib_figure_capture(self, mock_capture):
        """Test that matplotlib figures are captured."""
        # Mock a matplotlib figure
        mock_figure = Mock()
        mock_capture_obj = Mock()
        mock_capture_obj.figures = [mock_figure]
        mock_capture_obj.close_figures = Mock()
        mock_capture.return_value.__enter__.return_value = mock_capture_obj
        mock_capture.return_value.__exit__.return_value = None

        env = Environment()
        cell = Cell(CellType.CODE, "2 + 2", 1)  # Simple expression

        result = env.execute_cell(cell)

        # The figure should be captured and set as result instead of the expression result
        assert cell.result == mock_figure
        # The actual computation result should still be returned
        assert result == 4

    @patch("src.plaque.environment.capture_matplotlib_plots")
    def test_no_matplotlib_figures(self, mock_capture):
        """Test normal execution when no figures are created."""
        mock_capture_obj = Mock()
        mock_capture_obj.figures = []
        mock_capture_obj.close_figures = Mock()
        mock_capture.return_value.__enter__.return_value = mock_capture_obj
        mock_capture.return_value.__exit__.return_value = None

        env = Environment()
        cell = Cell(CellType.CODE, "42", 1)

        result = env.execute_cell(cell)

        assert result == 42
        assert cell.result == 42

    @patch("src.plaque.environment.capture_matplotlib_plots")
    def test_matplotlib_with_statements(self, mock_capture):
        """Test matplotlib capture with non-expression statements."""
        mock_figure = Mock()
        mock_capture_obj = Mock()
        mock_capture_obj.figures = [mock_figure]
        mock_capture_obj.close_figures = Mock()
        mock_capture.return_value.__enter__.return_value = mock_capture_obj
        mock_capture.return_value.__exit__.return_value = None

        env = Environment()
        cell = Cell(CellType.CODE, "x = 42", 1)  # Assignment, not expression

        result = env.execute_cell(cell)

        assert result is None
        assert cell.result == mock_figure  # Figure captured even for statements


class TestCompilationEdgeCases:
    """Test edge cases in code compilation."""

    def test_incomplete_statement(self):
        """Test incomplete statement handling."""
        env = Environment()
        cell = Cell(CellType.CODE, "if True:", 1)  # Incomplete if statement

        result = env.execute_cell(cell)

        assert result is None
        assert cell.error is not None
        assert "SyntaxError" in cell.error or "incomplete" in cell.error.lower()

    def test_complex_expression_parsing(self):
        """Test complex expression is handled correctly."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
import math
result = math.sqrt(16)
result + 1  # This should be treated as the expression to evaluate
""",
            1,
        )

        result = env.execute_cell(cell)

        assert result == 5.0  # sqrt(16) + 1 = 4 + 1 = 5
        assert cell.result == 5.0
        assert env.locals.get("result") == 4.0

    def test_multiline_expression(self):
        """Test multiline expression at end of cell."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """
x = 10
(x + 5
 + 3)  # Multiline expression
""",
            1,
        )

        result = env.execute_cell(cell)

        assert result == 18
        assert cell.result == 18


class TestCellTypeValidation:
    """Test cell type validation."""

    def test_markdown_cell_assertion(self):
        """Test that markdown cells raise assertion error."""
        env = Environment()
        cell = Cell(CellType.MARKDOWN, "# Markdown content", 1)

        with pytest.raises(AssertionError, match="Can only execute code cells"):
            env.execute_cell(cell)

    def test_code_cell_execution(self):
        """Test that code cells execute normally."""
        env = Environment()
        cell = Cell(CellType.CODE, "42", 1)

        result = env.execute_cell(cell)

        assert result == 42


class TestMemoryAndState:
    """Test memory management and state isolation."""

    def test_separate_environments(self):
        """Test that separate environments don't share state."""
        env1 = Environment()
        env2 = Environment()

        # Set variable in first environment
        cell1 = Cell(CellType.CODE, "x = 100", 1)
        env1.execute_cell(cell1)

        # Try to access in second environment
        cell2 = Cell(CellType.CODE, "x", 2)
        env2.execute_cell(cell2)

        assert env1.locals.get("x") == 100
        assert cell2.error is not None  # Should be NameError in env2
        assert "NameError" in cell2.error

    def test_environment_reuse(self):
        """Test that environment can be reused across multiple cells."""
        env = Environment()

        # Execute multiple cells in sequence
        cells = [
            Cell(CellType.CODE, "total = 0", 1),
            Cell(CellType.CODE, "total += 5", 2),
            Cell(CellType.CODE, "total *= 2", 3),
            Cell(CellType.CODE, "total", 4),
        ]

        results = []
        for cell in cells:
            result = env.execute_cell(cell)
            results.append(result)

        assert results == [None, None, None, 10]  # Only last cell returns value
        assert env.locals.get("total") == 10

    def test_import_persistence(self):
        """Test that imports persist between cells."""
        env = Environment()

        # Import in first cell
        cell1 = Cell(CellType.CODE, "import math", 1)
        env.execute_cell(cell1)

        # Use import in second cell
        cell2 = Cell(CellType.CODE, "result = math.sqrt(16)", 2)
        env.execute_cell(cell2)

        # Use import in third cell with expression
        cell3 = Cell(CellType.CODE, "math.pi", 3)
        result = env.execute_cell(cell3)

        assert cell1.error is None
        assert cell2.error is None
        assert cell3.error is None
        assert env.locals.get("result") == 4.0
        assert result == 3.141592653589793  # math.pi
        assert "math" in env.locals


class TestOutputCapture:
    """Test stdout and stderr capture functionality."""

    def test_stdout_capture(self):
        """Test that stdout is captured correctly."""
        env = Environment()
        cell = Cell(CellType.CODE, 'print("Hello, World!")', 1)

        env.execute_cell(cell)

        assert cell.stdout == "Hello, World!\n"
        assert cell.stderr == ""
        assert cell.result is None  # print returns None

    def test_stderr_capture(self):
        """Test that stderr is captured correctly."""
        env = Environment()
        cell = Cell(
            CellType.CODE, 'import sys\nprint("Error message", file=sys.stderr)', 1
        )

        env.execute_cell(cell)

        assert cell.stdout == ""
        assert cell.stderr == "Error message\n"
        assert cell.result is None

    def test_mixed_output_capture(self):
        """Test capturing both stdout and stderr."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """import sys
print("To stdout")
print("To stderr", file=sys.stderr)
print("More stdout")""",
            1,
        )

        env.execute_cell(cell)

        assert cell.stdout == "To stdout\nMore stdout\n"
        assert cell.stderr == "To stderr\n"

    def test_output_with_expression_result(self):
        """Test output capture when cell also returns a value."""
        env = Environment()
        cell = Cell(CellType.CODE, 'print("Computing...")\n42 + 8', 1)

        env.execute_cell(cell)

        assert cell.stdout == "Computing...\n"
        assert cell.stderr == ""
        assert cell.result == 50

    def test_output_capture_with_error(self):
        """Test that output is captured even when an error occurs."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """print("Before error")
import sys
print("Stderr before", file=sys.stderr)
x = 1 / 0  # This will raise ZeroDivisionError""",
            1,
        )

        env.execute_cell(cell)

        assert cell.stdout == "Before error\n"
        assert cell.stderr == "Stderr before\n"
        assert cell.error is not None
        assert "ZeroDivisionError" in cell.error

    def test_multiline_output(self):
        """Test capturing multiline output."""
        env = Environment()
        cell = Cell(
            CellType.CODE,
            """for i in range(3):
    print(f"Line {i}")""",
            1,
        )

        env.execute_cell(cell)

        assert cell.stdout == "Line 0\nLine 1\nLine 2\n"
        assert cell.stderr == ""

    def test_unicode_output(self):
        """Test capturing unicode output."""
        env = Environment()
        cell = Cell(CellType.CODE, 'print("Hello 🌍 Unicode! 你好")', 1)

        env.execute_cell(cell)

        assert cell.stdout == "Hello 🌍 Unicode! 你好\n"
        assert cell.stderr == ""


class TestMatplotlibImprovements:
    """Test improved matplotlib handling."""

    def test_matplotlib_backend_set(self):
        """Test that matplotlib backend is set to Agg."""
        # The backend is set at module import time
        try:
            import matplotlib

            backend = matplotlib.get_backend()
            # Backend should be Agg (case insensitive)
            assert backend.lower() == "agg"
        except ImportError:
            # If matplotlib is not installed, the test should pass
            pass

    @patch("src.plaque.environment.capture_matplotlib_plots")
    def test_context_manager_figures_prioritized(self, mock_capture):
        """Test that figures from context manager are properly used."""
        # Mock capture returns figures
        mock_figure = Mock()
        mock_capture_obj = Mock()
        mock_capture_obj.figures = [mock_figure]
        mock_capture_obj.close_figures = Mock()
        mock_capture.return_value.__enter__.return_value = mock_capture_obj
        mock_capture.return_value.__exit__.return_value = None

        env = Environment()
        cell = Cell(CellType.CODE, "2 + 2", 1)  # Simple expression

        env.execute_cell(cell)

        # Should use figure from context manager
        assert cell.result == mock_figure
        mock_capture_obj.close_figures.assert_called_once()

    def test_matplotlib_return_value_suppression(self):
        """Test that matplotlib return values are properly suppressed."""
        env = Environment()

        # Test matplotlib Text object is detected as matplotlib return value
        import matplotlib.pyplot as plt
        import matplotlib

        matplotlib.use("Agg")

        plt.figure()
        text_obj = plt.title("Test")

        is_matplotlib_return = env._is_matplotlib_return_value(text_obj)
        assert is_matplotlib_return

        plt.close("all")

    def test_matplotlib_figure_display_format(self):
        """Test that matplotlib figures are properly formatted for display."""
        from src.plaque.display import _handle_builtin_types

        # Test that non-matplotlib objects return None
        assert _handle_builtin_types("not a figure") is None
        assert _handle_builtin_types(42) is None

        # Test the class name detection
        mock_figure = Mock()
        mock_figure.__class__ = Mock()
        mock_figure.__class__.__name__ = "NotAFigure"
        assert _handle_builtin_types(mock_figure) is None
