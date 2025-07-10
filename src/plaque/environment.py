"""The main execution environment.

Represents a simple python environment with its own locals and globals."""

import ast
import sys
import traceback
from types import CodeType
from typing import Any, Optional
from contextlib import redirect_stdout, redirect_stderr
from .iowrapper import NotebookStdout
from .cell import Cell
from .display import capture_matplotlib_plots

import builtins

# Set matplotlib backend before any other matplotlib imports
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend to prevent segfaults
except ImportError:
    pass  # matplotlib not installed


class Environment:
    def __init__(self):
        self.locals = {"__name__": "__main__"}
        self.globals = self.locals  # Use same namespace for globals and locals
        self.counter = 0

    def eval(self, source: str | CodeType):
        return builtins.eval(source, self.globals, self.locals)

    def exec(self, source: str | CodeType):
        return builtins.exec(source, self.globals, self.locals)

    def compile(self, source, mode="exec"):
        try:
            return builtins.compile(source, "<cell>", mode)
        except SyntaxError as e:
            return None, str(e)

    def execute_cell(self, cell: Cell):
        """Execute a code cell with proper error handling and rich display."""
        assert cell.is_code, "Can only execute code cells."

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""
        cell.counter = self.counter
        self.counter += 1

        # Create buffers for output capture
        stdout_buffer = NotebookStdout(sys.stdout)
        stderr_buffer = NotebookStdout(sys.stderr)

        try:
            # Parse the cell content
            try:
                tree = ast.parse(cell.content)
                stmts = list(ast.iter_child_nodes(tree))
            except SyntaxError as e:
                # Handle syntax errors with better formatting
                cell.error = self._format_syntax_error(e, cell.content)
                return None

            if not stmts:
                return None

            # Capture matplotlib plots and output during execution
            result = None
            is_expression_cell = isinstance(stmts[-1], ast.Expr)

            with capture_matplotlib_plots() as figure_capture:
                try:
                    if is_expression_cell:
                        # Expression cell
                        with (
                            redirect_stdout(stdout_buffer),
                            redirect_stderr(stderr_buffer),
                        ):
                            # The last statement is an expression - execute preceding statements
                            if len(stmts) > 1:
                                exec_code = self.compile(
                                    ast.Module(body=stmts[:-1], type_ignores=[]),
                                    "exec",  # type: ignore
                                )
                                if isinstance(exec_code, tuple):  # Error occurred
                                    cell.error = exec_code[1]
                                    return None
                                self.exec(exec_code)

                            # Evaluate the last expression
                            eval_code = self.compile(ast.unparse(stmts[-1]), "eval")
                            if isinstance(eval_code, tuple):  # Error occurred
                                cell.error = eval_code[1]
                                return None

                            result = self.eval(eval_code)

                            # Capture any output
                            cell.stdout = stdout_buffer.getvalue()
                            cell.stderr = stderr_buffer.getvalue()

                    else:
                        # Statement cell
                        with (
                            redirect_stdout(stdout_buffer),
                            redirect_stderr(stderr_buffer),
                        ):
                            code_obj = self.compile(cell.content, "exec")
                            if isinstance(code_obj, tuple):  # Error occurred
                                cell.error = code_obj[1]
                                return None

                            self.exec(code_obj)

                            # Capture any output
                            cell.stdout = stdout_buffer.getvalue()
                            cell.stderr = stderr_buffer.getvalue()

                except Exception as inner_e:
                    # Clean up figures in case of exception
                    figure_capture.close_figures()
                    raise inner_e

            # Use captured figures from the context manager (after context manager is done)
            if figure_capture.figures:
                # Display the first captured figure
                cell.result = figure_capture.figures[0]
            elif (
                is_expression_cell
                and result is not None
                and self._is_matplotlib_return_value(result)
            ):
                # If result is a matplotlib return value but no figures captured,
                # suppress it (don't display matplotlib internal objects)
                cell.result = None
            elif is_expression_cell and result is not None:
                cell.result = result

            # Clean up matplotlib figures after processing
            figure_capture.close_figures()

            return result

        except Exception as e:
            # Capture any output before the error
            cell.stdout = stdout_buffer.getvalue()
            cell.stderr = stderr_buffer.getvalue()
            # Capture runtime errors with better formatting
            cell.error = self._format_runtime_error(e, cell.content)
            return None
        finally:
            # Close buffers
            stdout_buffer.close()
            stderr_buffer.close()

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
