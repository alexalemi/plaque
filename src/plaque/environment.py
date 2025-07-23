"""The main execution environment.

Supports both legacy simple python environment and new IPython-based environment."""

import ast
import sys
import traceback
from types import CodeType
from typing import Any
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
    matplotlib = None

# Import IPython components
try:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.displayhook import DisplayHook
    from IPython.utils.capture import capture_output
    import IPython.core.magic_arguments as magic_arguments

    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False


class PlaqueDisplayHook(DisplayHook):
    """Custom DisplayHook that integrates with plaque's Cell structure."""

    def __init__(self, shell, current_cell=None):
        super().__init__(shell)
        self.current_cell = current_cell

    def set_current_cell(self, cell):
        """Set the current cell for result storage."""
        self.current_cell = cell

    def write_output_prompt(self):
        """Override to suppress 'Out[n]:' prefixes."""
        pass  # Don't write any output prompt

    def compute_format_data(self, result):
        """Compute format data using IPython's formatters."""
        # We don't need to store the result here since we get it from ExecutionResult
        # Just let IPython handle the formatting
        return super().compute_format_data(result)

    def write_format_data(self, format_dict, md_dict=None):
        """Store formatted data in the current cell instead of printing."""
        # The result is already stored in compute_format_data
        # We could enhance this to store formatted representations too
        pass

    def finish_displayhook(self):
        """Override to manage execution counter sync."""
        super().finish_displayhook()
        if self.current_cell is not None:
            self.current_cell.counter = self.shell.execution_count


class IPythonEnvironment:
    """IPython-based execution environment with full IPython feature support."""

    def __init__(self):
        if not IPYTHON_AVAILABLE:
            raise ImportError("IPython is required for IPythonEnvironment")

        # Create IPython shell instance
        self.shell = InteractiveShell.instance()

        # Configure the shell
        self._configure_shell()

        # Set up custom display hook
        self.display_hook = PlaqueDisplayHook(self.shell)
        self.shell.displayhook = self.display_hook

        # Store reference to enable counter access
        self._execution_count = 0

    def _configure_shell(self):
        """Configure IPython shell for notebook use."""
        # Enable matplotlib inline backend
        if matplotlib:
            try:
                self.shell.enable_matplotlib("inline")
            except NotImplementedError:
                # Fallback: configure matplotlib manually for non-GUI environment
                import matplotlib.pyplot as plt

                plt.ioff()  # Turn off interactive mode
                # The backend is already set to Agg in the imports

        # Configure shell settings
        self.shell.ast_node_interactivity = "last_expr_or_assign"
        self.shell.autoindent = False

        # Set up custom pager hook for help output
        # Note: Pager customization is complex and version-dependent
        # For now, we'll keep the default pager behavior
        # TODO: Implement custom pager hook when needed

    @property
    def counter(self):
        """Get current execution counter."""
        return self.shell.execution_count

    @property
    def locals(self):
        """Access to local namespace (same as globals in IPython)."""
        return self.shell.user_ns

    @property
    def globals(self):
        """Access to global namespace."""
        return self.shell.user_ns

    def execute_cell(self, cell: Cell):
        """Execute a code cell using IPython's run_cell."""
        assert cell.is_code, "Can only execute code cells."

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""

        # Set current cell in display hook
        self.display_hook.set_current_cell(cell)

        try:
            # Use IPython's built-in output capture
            with capture_output() as captured:
                # Execute the cell using IPython (non-silent to get proper results)
                result = self.shell.run_cell(
                    cell.content, store_history=True, silent=False
                )

            # Store captured output, filtering out the Out[n]: prompt
            raw_stdout = captured.stdout
            # Remove "Out[n]: " pattern from the beginning of lines
            import re

            filtered_stdout = re.sub(
                r"^Out\[\d+\]: ", "", raw_stdout, flags=re.MULTILINE
            )
            cell.stdout = filtered_stdout
            cell.stderr = captured.stderr

            # Handle execution result
            if result.error_before_exec:
                cell.error = str(result.error_before_exec)
            elif result.error_in_exec:
                cell.error = self._format_exception(result.error_in_exec)
            else:
                # Get the result from the user namespace (populated by displayhook)
                cell.result = self.shell.user_ns.get("_", None)

            # Update counter
            cell.counter = self.shell.execution_count

            return cell.result

        except Exception as e:
            cell.error = self._format_exception(e)
            return None
        finally:
            # Clear current cell reference
            self.display_hook.set_current_cell(None)

    def _format_exception(self, exc):
        """Format exception for display in notebook."""
        # Use IPython's exception formatting if available
        if hasattr(self.shell, "showtraceback"):
            # Capture the formatted traceback
            import io
            from contextlib import redirect_stderr

            error_buffer = io.StringIO()
            with redirect_stderr(error_buffer):
                self.shell.showtraceback()

            return error_buffer.getvalue().strip()
        else:
            # Fallback to basic formatting
            return f"{type(exc).__name__}: {exc}"

    async def execute_cell_async(self, cell: Cell):
        """Execute a code cell asynchronously using IPython's run_cell_async."""
        assert cell.is_code, "Can only execute code cells."

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""

        # Set current cell in display hook
        self.display_hook.set_current_cell(cell)

        try:
            # Use IPython's built-in output capture
            with capture_output() as captured:
                # Execute the cell using IPython's async runner (non-silent to get proper results)
                result = await self.shell.run_cell_async(
                    cell.content, store_history=True, silent=False
                )

            # Store captured output, filtering out the Out[n]: prompt
            raw_stdout = captured.stdout
            # Remove "Out[n]: " pattern from the beginning of lines
            import re

            filtered_stdout = re.sub(
                r"^Out\[\d+\]: ", "", raw_stdout, flags=re.MULTILINE
            )
            cell.stdout = filtered_stdout
            cell.stderr = captured.stderr

            # Handle execution result
            if result.error_before_exec:
                cell.error = str(result.error_before_exec)
            elif result.error_in_exec:
                cell.error = self._format_exception(result.error_in_exec)
            else:
                # Get the result from the user namespace (populated by displayhook)
                cell.result = self.shell.user_ns.get("_", None)

            # Update counter
            cell.counter = self.shell.execution_count

            return cell.result

        except Exception as e:
            cell.error = self._format_exception(e)
            return None
        finally:
            # Clear current cell reference
            self.display_hook.set_current_cell(None)


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


# Factory function to create the appropriate environment
def create_environment(use_ipython=True):
    """Create an execution environment.

    Args:
        use_ipython: If True and IPython is available, use IPythonEnvironment.
                    Otherwise, use legacy Environment.
    """
    if use_ipython and IPYTHON_AVAILABLE:
        return IPythonEnvironment()
    else:
        return Environment()
