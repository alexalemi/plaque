"""The main execution environment using IPython.

Provides a full IPython execution environment with support for:
- Magic commands (%timeit, %matplotlib, etc.)
- Top-level async/await
- Rich display output
- Enhanced error formatting
"""

import re
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from IPython.core.interactiveshell import InteractiveShell
from IPython.core.displayhook import DisplayHook

from .iowrapper import NotebookStdout
from .cell import Cell
from .display import capture_matplotlib_plots

# ANSI color code to CSS color mapping
ANSI_COLORS = {
    '30': 'black',
    '31': '#e74c3c',      # red
    '32': '#2ecc71',      # green
    '33': '#f39c12',      # yellow
    '34': '#3498db',      # blue
    '35': '#9b59b6',      # magenta
    '36': '#1abc9c',      # cyan
    '37': 'white',
    '39': None,           # default/reset
    '90': '#7f8c8d',      # bright black (gray)
    '91': '#e74c3c',      # bright red
    '92': '#2ecc71',      # bright green
    '93': '#f1c40f',      # bright yellow
    '94': '#3498db',      # bright blue
    '95': '#9b59b6',      # bright magenta
    '96': '#1abc9c',      # bright cyan
    '97': 'white',        # bright white
}

# Extended 256-color palette codes (38;5;N format)
ANSI_256_COLORS = {
    '28': '#008700',      # green
    '124': '#af0000',     # dark red
    '160': '#d70000',     # red
    '166': '#d75f00',     # orange
    '196': '#ff0000',     # bright red
}


def ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML span elements with colors."""
    result = []
    i = 0
    current_color = None

    while i < len(text):
        # Check for ANSI escape sequence
        if text[i:i+2] == '\x1b[':
            # Find the end of the escape sequence
            end = text.find('m', i)
            if end != -1:
                # Extract the codes
                codes = text[i+2:end]

                # Handle reset (0) or default color (39)
                if codes in ('0', '39', ''):
                    if current_color:
                        result.append('</span>')
                        current_color = None
                # Handle 256-color codes (38;5;N)
                elif codes.startswith('38;5;'):
                    color_num = codes[5:]
                    color = ANSI_256_COLORS.get(color_num)
                    if color:
                        if current_color:
                            result.append('</span>')
                        result.append(f'<span style="color: {color}">')
                        current_color = color
                # Handle standard colors
                else:
                    # Get the last code (in case of combined codes like 1;31)
                    code_parts = codes.split(';')
                    for code in code_parts:
                        color = ANSI_COLORS.get(code)
                        if color:
                            if current_color:
                                result.append('</span>')
                            result.append(f'<span style="color: {color}">')
                            current_color = color
                        elif code == '0' or color is None and code in ANSI_COLORS:
                            if current_color:
                                result.append('</span>')
                                current_color = None

                i = end + 1
                continue

        # Regular character - escape HTML entities
        char = text[i]
        if char == '<':
            result.append('&lt;')
        elif char == '>':
            result.append('&gt;')
        elif char == '&':
            result.append('&amp;')
        else:
            result.append(char)
        i += 1

    # Close any open span
    if current_color:
        result.append('</span>')

    return ''.join(result)


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes (color codes) from a string."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


# Set matplotlib backend before any other matplotlib imports
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend to prevent segfaults
except ImportError:
    pass  # matplotlib not installed


class SilentDisplayHook(DisplayHook):
    """A display hook that captures results without printing."""

    def __init__(self, shell, *args, **kwargs):
        super().__init__(shell, *args, **kwargs)
        self.captured_result = None

    def __call__(self, result=None):
        """Override to capture result without printing."""
        if result is not None:
            self.captured_result = result
            # Still update user_ns with _, __, ___, etc.
            self.update_user_ns(result)

    def reset_capture(self):
        """Reset the captured result for a new cell."""
        self.captured_result = None


class Environment:
    """IPython-based execution environment for plaque notebooks.

    Uses IPython's InteractiveShell to provide:
    - Magic command support (%timeit, %matplotlib, %%time, etc.)
    - Top-level async/await
    - Rich display integration
    - Better error messages
    """

    def __init__(self):
        # Create a NEW IPython shell instance (not the singleton)
        # This ensures each Environment has its own namespace
        self.shell = InteractiveShell()

        # Configure the shell for notebook-like behavior
        self.shell.ast_node_interactivity = "last_expr"  # Only show last expression

        # Enable top-level async support
        self.shell.autoawait = True

        # Install our silent display hook to capture results without printing
        # IMPORTANT: Must also update display_trap.hook, not just shell.displayhook
        self.display_hook = SilentDisplayHook(self.shell)
        self.shell.displayhook = self.display_hook
        self.shell.display_trap.hook = self.display_hook

        # Disable automatic traceback printing - we'll format errors ourselves
        # This prevents IPython from printing tracebacks to stdout
        self.shell.showtraceback = lambda *args, **kwargs: None

        # Set up the namespace
        self.shell.user_ns["__name__"] = "__main__"

        # Execution counter
        self.counter = 0

    @property
    def locals(self) -> dict:
        """Access to the user namespace (for compatibility)."""
        return self.shell.user_ns

    @property
    def globals(self) -> dict:
        """Access to the user namespace (for compatibility)."""
        return self.shell.user_ns

    def execute_cell(self, cell: Cell):
        """Execute a code cell using IPython with proper error handling and rich display.

        Supports:
        - Magic commands (line and cell magics)
        - Top-level async/await
        - Rich display output
        - Matplotlib figure capture
        """
        assert cell.is_code, "Can only execute code cells."

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""
        cell.counter = self.counter
        self.counter += 1

        # Reset display hook capture
        self.display_hook.reset_capture()

        # Create buffers for output capture
        stdout_buffer = NotebookStdout(sys.stdout)
        stderr_buffer = NotebookStdout(sys.stderr)

        try:
            result = None

            # Capture matplotlib plots during execution
            with capture_matplotlib_plots() as figure_capture:
                try:
                    with (
                        redirect_stdout(stdout_buffer),
                        redirect_stderr(stderr_buffer),
                    ):
                        # Execute the cell using IPython
                        exec_result = self.shell.run_cell(
                            cell.content,
                            store_history=False,  # Don't store in IPython history
                            silent=False,  # Allow result to be captured
                        )

                        # Capture any output
                        cell.stdout = stdout_buffer.getvalue()
                        cell.stderr = stderr_buffer.getvalue()

                        # Check for errors
                        if exec_result.error_before_exec:
                            cell.error = self._format_error(exec_result.error_before_exec)
                            return None

                        if exec_result.error_in_exec:
                            cell.error = self._format_error(exec_result.error_in_exec)
                            return None

                        # Get the result - IPython returns it in exec_result.result
                        result = exec_result.result
                        if result is None:
                            # Also check our display hook
                            result = self.display_hook.captured_result

                except Exception as inner_e:
                    # Clean up figures in case of exception
                    figure_capture.close_figures()
                    raise inner_e

            # Use captured figures from the context manager
            if figure_capture.figures:
                # Display the first captured figure
                cell.result = figure_capture.figures[0]
            elif result is not None and self._is_matplotlib_return_value(result):
                # If result is a matplotlib return value but no figures captured,
                # suppress it (don't display matplotlib internal objects)
                cell.result = None
            elif result is not None:
                cell.result = result

            # Clean up matplotlib figures after processing
            figure_capture.close_figures()

            return result

        except Exception as e:
            # Capture any output before the error
            cell.stdout = stdout_buffer.getvalue()
            cell.stderr = stderr_buffer.getvalue()
            # Capture runtime errors with better formatting
            cell.error = self._format_error(e)
            return None
        finally:
            # Close buffers
            stdout_buffer.close()
            stderr_buffer.close()

    def _format_error(self, error: Exception) -> str:
        """Format an error for display.

        Uses IPython's traceback formatting when available, converting
        ANSI color codes to HTML for colored display.
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # For SyntaxErrors, provide context
        if isinstance(error, SyntaxError):
            parts = [f"SyntaxError: {error.msg}"]
            if error.text:
                parts.append(f"\n  {error.text.rstrip()}")
                if error.offset:
                    parts.append("  " + " " * (error.offset - 1) + "^")
            return "\n".join(parts)

        # For other errors, use IPython's formatting if available
        try:
            # Get the formatted traceback from IPython
            tb_lines = self.shell.InteractiveTB.structured_traceback(
                type(error), error, error.__traceback__
            )
            # Filter out internal plaque frames
            filtered_lines = []
            skip_next = False
            for line in tb_lines:
                # Strip ANSI codes for filtering check
                clean_line = strip_ansi_codes(line)
                if skip_next:
                    skip_next = False
                    continue
                if "plaque/" in clean_line or "environment.py" in clean_line:
                    skip_next = True  # Skip the code line that follows
                    continue
                filtered_lines.append(line)

            if filtered_lines:
                # Convert ANSI codes to HTML for the final result
                raw_result = "\n".join(filtered_lines)
                return ansi_to_html(raw_result)
        except Exception:
            pass

        # Fallback to simple error message
        return f"{error_type}: {error_msg}"

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


# For backwards compatibility, provide eval/exec methods
# Note: These bypass IPython and use plain Python execution
class LegacyEnvironment:
    """Legacy environment using plain Python exec/eval.

    Provided for backwards compatibility. Prefer Environment for new code.
    """

    def __init__(self):
        self.locals = {"__name__": "__main__"}
        self.globals = self.locals
        self.counter = 0

    def eval(self, source):
        import builtins
        return builtins.eval(source, self.globals, self.locals)

    def exec(self, source):
        import builtins
        return builtins.exec(source, self.globals, self.locals)

    def compile(self, source, mode="exec"):
        import builtins
        try:
            return builtins.compile(source, "<cell>", mode)
        except SyntaxError as e:
            return None, str(e)
