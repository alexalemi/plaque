"""The main execution environment.

Represents an IPython-based execution environment with rich features."""

import traceback
from types import CodeType
from typing import Any
from .cell import Cell
from .display import capture_matplotlib_plots

import builtins

# Import IPython components
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
from traitlets.config import Config

# Set matplotlib backend before any other matplotlib imports
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend to prevent segfaults
except ImportError:
    pass  # matplotlib not installed


class Environment:
    def __init__(self):
        # Configure IPython for notebook-like behavior
        config = Config()
        config.InteractiveShell.ast_node_interactivity = "last_expr"
        config.InteractiveShell.show_rewritten_input = False
        config.InteractiveShell.quiet = True
        config.PlainTextFormatter.max_width = 120

        # Create IPython shell instance
        self.shell = InteractiveShell.instance(config=config)

        # Enable async support for top-level await
        self.shell.autoawait = True

        # Set up namespace - IPython manages its own namespace
        self.shell.user_ns["__name__"] = "__main__"

        self.counter = 0

    def eval(self, source: str | CodeType):
        """Evaluate code using IPython shell."""
        if isinstance(source, str):
            return self.shell.ev(source)
        else:
            # For compiled code objects, fall back to built-in eval
            return builtins.eval(source, self.shell.user_global_ns, self.shell.user_ns)

    def exec(self, source: str | CodeType):
        """Execute code using IPython shell."""
        if isinstance(source, str):
            return self.shell.ex(source)
        else:
            # For compiled code objects, fall back to built-in exec
            return builtins.exec(source, self.shell.user_global_ns, self.shell.user_ns)

    def compile(self, source, mode="exec"):
        """Compile code - delegate to IPython's compilation."""
        try:
            # Use IPython's compile to handle magic commands and other special syntax
            compiled = self.shell.compile(source, "<cell>", mode)
            return compiled
        except SyntaxError as e:
            return None, str(e)

    def execute_cell(self, cell: Cell):
        """Execute a code cell using IPython with proper error handling and rich display."""
        assert cell.is_code, "Can only execute code cells."

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""
        cell.counter = self.counter
        self.counter += 1

        try:
            # Use IPython's capture_output to capture stdout/stderr
            with capture_output() as captured:
                # Also capture matplotlib plots
                with capture_matplotlib_plots() as figure_capture:
                    try:
                        # Use IPython's run_cell method which handles magic commands,
                        # async/await, and expression vs statement detection automatically
                        result = self.shell.run_cell(
                            cell.content, store_history=True, silent=False
                        )

                        # Extract the execution result
                        if result.result is not None:
                            cell.result = result.result
                        elif result.error_before_exec:
                            # Syntax or compilation error
                            cell.error = str(result.error_before_exec)
                            return None
                        elif result.error_in_exec:
                            # Runtime error
                            cell.error = self._format_ipython_error(
                                result.error_in_exec
                            )
                            return None

                    except Exception as e:
                        # Clean up figures in case of exception
                        figure_capture.close_figures()
                        cell.error = self._format_runtime_error(e, cell.content)
                        return None

            # Capture output from IPython
            cell.stdout = captured.stdout
            cell.stderr = captured.stderr

            # Handle matplotlib figures
            if figure_capture.figures:
                # If we have matplotlib figures, prioritize the first one
                cell.result = figure_capture.figures[0]
            elif cell.result is not None and self._is_matplotlib_return_value(
                cell.result
            ):
                # Suppress matplotlib return values if no figures were captured
                cell.result = None

            # Clean up matplotlib figures after processing
            figure_capture.close_figures()

            return cell.result

        except Exception as e:
            # Fallback error handling
            cell.error = self._format_runtime_error(e, cell.content)
            return None

    def _format_ipython_error(self, error_in_exec) -> str:
        """Format an IPython execution error with cleaned traceback."""
        if hasattr(error_in_exec, "etype") and hasattr(error_in_exec, "evalue"):
            # IPython ExecutionResult error format
            error_type = (
                error_in_exec.etype.__name__ if error_in_exec.etype else "Error"
            )
            error_msg = (
                str(error_in_exec.evalue) if error_in_exec.evalue else "Unknown error"
            )

            # Use IPython's traceback formatting
            if hasattr(error_in_exec, "traceback") and error_in_exec.traceback:
                # Join traceback lines and clean them
                tb_lines = error_in_exec.traceback
                cleaned_lines = []

                for line in tb_lines:
                    # Filter out internal IPython and plaque frames
                    if not any(
                        internal in line
                        for internal in [
                            "site-packages/IPython/",
                            "plaque/environment.py",
                            "plaque/processor.py",
                        ]
                    ):
                        cleaned_lines.append(line.rstrip())

                if cleaned_lines:
                    return "\n".join([f"{error_type}: {error_msg}", ""] + cleaned_lines)

            return f"{error_type}: {error_msg}"
        else:
            # Fallback to standard formatting
            return self._format_runtime_error(error_in_exec, "")

    def _format_syntax_error(self, error: SyntaxError, source: str) -> str:
        """Format a syntax error with context and highlighting."""
        lines = source.split("\n")
        error_line = error.lineno if error.lineno else 1

        # Build error message
        parts = [f"SyntaxError: {error.msg}"]

        # Add context around the error line
        start_line = max(1, error_line - 2)
        end_line = min(len(lines), error_line + 2)

        parts.append("\nContext:")
        for i in range(start_line, end_line + 1):
            if i <= len(lines):
                line_content = lines[i - 1] if i <= len(lines) else ""
                prefix = ">>> " if i == error_line else "    "
                parts.append(f"{prefix}{i:3d}: {line_content}")

                # Add pointer to error column
                if i == error_line and error.offset:
                    pointer_line = " " * (len(prefix) + 4 + error.offset - 1) + "^"
                    parts.append(pointer_line)

        return "\n".join(parts)

    def _is_matplotlib_return_value(self, result: Any) -> bool:
        """Check if result is a matplotlib return value that should be suppressed."""
        if result is None:
            return False

        try:
            # Check for common matplotlib return types
            result_type = str(type(result))

            # List of return values - check if it contains matplotlib objects
            if isinstance(result, list) and result:
                first_item_type = str(type(result[0]))
                if any(
                    mpl_type in first_item_type.lower()
                    for mpl_type in [
                        "matplotlib",
                        "line2d",
                        "text",
                        "patch",
                        "collection",
                    ]
                ):
                    return True

            # Direct matplotlib objects
            if any(
                mpl_type in result_type.lower()
                for mpl_type in ["matplotlib", "axes", "figure"]
            ):
                return True

            return False
        except Exception:
            return False

    def _format_runtime_error(self, error: Exception, source: str) -> str:
        """Format a runtime error with cleaned traceback."""
        error_type = type(error).__name__
        error_msg = str(error)

        # Get full traceback
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)

        # Find the line in our cell that caused the error
        cell_tb_lines = []
        in_cell = False

        for line in tb_lines:
            if "<cell>" in line:
                in_cell = True
                # Extract line number from traceback
                if "line " in line:
                    try:
                        line_num_str = line.split("line ")[1].split(",")[0]
                        line_num = int(line_num_str)
                        cell_tb_lines.append(f"  Line {line_num} in cell")
                    except IndexError:
                        cell_tb_lines.append("  In cell")
            elif in_cell and not any(
                internal in line
                for internal in ["plaque/", "environment.py", 'File "/']
            ):
                # This is the code line that caused the error
                cell_tb_lines.append(f"    {line.strip()}")
            elif "Traceback" in line:
                continue  # Skip the "Traceback (most recent call last):" line
            elif not any(
                internal in line
                for internal in ["plaque/", "environment.py", "site-packages/"]
            ):
                # Include other relevant traceback info
                cell_tb_lines.append(line.rstrip())

        if cell_tb_lines:
            # Build a clean error message
            result = [f"{error_type}: {error_msg}"]
            result.append("\nTraceback:")
            result.extend(cell_tb_lines)
            return "\n".join(result)
        else:
            # Fallback to simple error message
            return f"{error_type}: {error_msg}"
