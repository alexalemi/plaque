"""IPython-based execution environment for plaque notebooks.

This module provides an alternative execution backend that uses IPython kernels
instead of Python's exec/eval, enabling features like top-level await and magic commands.
"""

from typing import Any, Dict, Optional

from .cell import Cell
from .environment import BaseEnvironment
from .ipython_kernel import IPythonKernelManager


class IPythonEnvironment(BaseEnvironment):
    """Execution environment that uses an IPython kernel.

    This environment provides full IPython capabilities including:
    - Top-level await support
    - Magic commands (%time, %debug, etc.)
    - Shell commands (!ls, !pip install, etc.)
    - Better error handling and debugging
    - IPython extensions
    """

    def __init__(self, kernel_name: str = "python3", timeout: float = 30.0):
        """Initialize the IPython environment.

        Args:
            kernel_name: Name of the kernel to use (default: python3)
            timeout: Default execution timeout in seconds
        """
        super().__init__()
        self.kernel_name = kernel_name
        self.timeout = timeout
        self.kernel: Optional[IPythonKernelManager] = None
        self._started = False

    def start(self) -> None:
        """Start the IPython kernel if not already running."""
        if not self._started:
            self.kernel = IPythonKernelManager(
                kernel_name=self.kernel_name, timeout=self.timeout
            )
            self.kernel.start()
            self._started = True

    def stop(self) -> None:
        """Stop the IPython kernel."""
        if self._started and self.kernel is not None:
            self.kernel.stop()
            self.kernel = None
            self._started = False

    def reset(self) -> None:
        """Reset the environment by restarting the kernel."""
        if self._started and self.kernel is not None:
            self.kernel.restart()
            self.counter = 0
        else:
            self.start()

    def get_namespace(self) -> Dict[str, Any]:
        """Get the current namespace from the IPython kernel."""
        if not self._started:
            return {}
        return self.kernel.get_namespace()

    def execute_cell(self, cell: Cell) -> Any:
        """Execute a code cell using the IPython kernel.

        Args:
            cell: The cell to execute

        Returns:
            The result of the cell execution, if any
        """
        assert cell.is_code, "Can only execute code cells."

        # Start kernel if needed
        if not self._started:
            self.start()

        # Clear previous results
        cell.result = None
        cell.error = None
        cell.stdout = ""
        cell.stderr = ""
        cell.counter = self.counter
        self.counter += 1

        try:
            # Execute code in IPython kernel
            result = self.kernel.execute(cell.content, timeout=self.timeout)

            # Copy results to cell
            cell.stdout = result.stdout
            cell.stderr = result.stderr
            cell.error = result.error

            # Handle execution result
            if result.output:
                # Convert IPython output format to plaque format
                cell.result = self._convert_output(result.output)

            # Handle display data (plots, html, etc)
            if result.display_data:
                # If we have display data but no output, use the first display item
                if cell.result is None and result.display_data:
                    cell.result = self._convert_output(result.display_data[0])

            # Update execution counter
            if result.execution_count > 0:
                cell.counter = result.execution_count
                self.counter = result.execution_count + 1

            return cell.result

        except Exception as e:
            # Capture any errors
            cell.error = f"{type(e).__name__}: {str(e)}"
            return None

    def _convert_output(self, output_data: Dict[str, Any]) -> Any:
        """Convert IPython output format to plaque format.

        Args:
            output_data: Dictionary of MIME type to data from IPython

        Returns:
            Converted output suitable for plaque's display system
        """
        # Priority order for output types (similar to Jupyter)
        mime_priority = [
            "text/html",
            "text/markdown",
            "image/png",
            "image/jpeg",
            "text/plain",
        ]

        # Special handling for DataFrames
        if "text/html" in output_data and "<table" in output_data["text/html"]:
            # This is likely a DataFrame, return the HTML directly
            return output_data["text/html"]

        # Find the best mime type available
        for mime_type in mime_priority:
            if mime_type in output_data:
                data = output_data[mime_type]

                # For images, we need to decode base64
                if mime_type.startswith("image/"):
                    import base64
                    from io import BytesIO

                    try:
                        from PIL import Image

                        img_bytes = base64.b64decode(data)
                        return Image.open(BytesIO(img_bytes))
                    except ImportError:
                        # PIL not available, return raw data
                        return data

                # For text/plain, strip quotes if it's a string representation
                elif mime_type == "text/plain":
                    # IPython often quotes strings, remove outer quotes if present
                    if isinstance(data, str) and len(data) >= 2:
                        if (data[0] == '"' and data[-1] == '"') or (
                            data[0] == "'" and data[-1] == "'"
                        ):
                            return data[1:-1]
                    return data

                else:
                    return data

        # No suitable output found
        return None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
