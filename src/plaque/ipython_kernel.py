"""IPython kernel integration for plaque notebooks.

This module provides a wrapper around jupyter_client to manage IPython kernels
for executing notebook cells with full IPython capabilities including top-level await.
"""

import queue
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from jupyter_client import KernelManager
    from jupyter_client.blocking import BlockingKernelClient

    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False
    KernelManager = None
    BlockingKernelClient = None


@dataclass
class ExecutionResult:
    """Result of executing code in an IPython kernel."""

    output: Any = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    execution_count: int = 0
    display_data: List[Dict[str, Any]] = field(default_factory=list)


class IPythonKernelManager:
    """Manages an IPython kernel for notebook execution.

    This class handles:
    - Kernel lifecycle (start, stop, restart)
    - Code execution with message handling
    - Output capture from multiple channels
    - Conversion of IPython output to plaque format
    """

    def __init__(self, kernel_name: str = "python3", timeout: float = 10.0):
        """Initialize the kernel manager.

        Args:
            kernel_name: Name of the kernel to use (default: python3)
            timeout: Default timeout for operations in seconds
        """
        if not JUPYTER_AVAILABLE:
            raise ImportError(
                "jupyter_client is required for IPython kernel support. "
                "Install with: pip install jupyter-client ipykernel"
            )

        self.kernel_name = kernel_name
        self.timeout = timeout
        self.km: Optional[KernelManager] = None
        self.kc: Optional[BlockingKernelClient] = None
        self._execution_count = 0

    def start(self) -> None:
        """Start the IPython kernel."""
        if self.km is not None:
            raise RuntimeError("Kernel is already running")

        # Create and start kernel manager
        self.km = KernelManager(kernel_name=self.kernel_name)
        self.km.start_kernel()

        # Create blocking client
        self.kc = self.km.blocking_client()
        self.kc.start_channels()

        # Wait for kernel to be ready
        self.kc.wait_for_ready(timeout=self.timeout)

    def stop(self) -> None:
        """Stop the IPython kernel and cleanup."""
        if self.kc is not None:
            self.kc.stop_channels()
            self.kc = None

        if self.km is not None:
            self.km.shutdown_kernel()
            self.km = None

        self._execution_count = 0

    def restart(self) -> None:
        """Restart the IPython kernel."""
        self.stop()
        self.start()

    def is_alive(self) -> bool:
        """Check if the kernel is alive and responsive."""
        if self.km is None or self.kc is None:
            return False
        return self.km.is_alive()

    def execute(self, code: str, timeout: Optional[float] = None) -> ExecutionResult:
        """Execute code in the IPython kernel and return results.

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (uses default if None)

        Returns:
            ExecutionResult containing output, stdout, stderr, errors, and display data
        """
        if self.kc is None:
            raise RuntimeError("Kernel is not running. Call start() first.")

        if timeout is None:
            timeout = self.timeout

        # Clear any pending messages
        while True:
            try:
                self.kc.get_iopub_msg(timeout=0.01)
            except queue.Empty:
                break

        # Send execute request
        msg_id = self.kc.execute(code, allow_stdin=False)

        # Initialize result
        result = ExecutionResult()
        execution_done = False

        # Process messages from kernel
        deadline = time.time() + timeout
        while not execution_done and time.time() < deadline:
            try:
                # Get message with short timeout to allow checking deadline
                msg = self.kc.get_iopub_msg(timeout=0.1)

                # Skip messages from other executions
                if msg["parent_header"].get("msg_id") != msg_id:
                    continue

                content = msg["content"]
                msg_type = msg["msg_type"]

                if msg_type == "stream":
                    # stdout/stderr output
                    stream_name = content["name"]
                    text = content["text"]
                    if stream_name == "stdout":
                        result.stdout += text
                    elif stream_name == "stderr":
                        result.stderr += text

                elif msg_type == "execute_result":
                    # Execution result (like eval output)
                    result.output = content["data"]
                    result.execution_count = content["execution_count"]
                    self._execution_count = result.execution_count

                elif msg_type == "display_data":
                    # Rich display output (plots, html, etc)
                    result.display_data.append(content["data"])

                elif msg_type == "error":
                    # Execution error
                    result.error = self._format_error(
                        content["ename"], content["evalue"], content["traceback"]
                    )

                elif msg_type in ("execute_input", "execute_reply"):
                    # Execution metadata
                    if msg_type == "execute_reply":
                        execution_done = True
                        if "execution_count" in content:
                            self._execution_count = content["execution_count"]

                elif msg_type == "status":
                    # Kernel status change
                    if content["execution_state"] == "idle":
                        execution_done = True

            except queue.Empty:
                # No message available within timeout
                continue

        # Check if execution timed out
        if not execution_done:
            result.error = f"Execution timed out after {timeout} seconds"

        # If no execution count was set, use internal counter
        if result.execution_count == 0:
            result.execution_count = self._execution_count

        return result

    def _format_error(self, ename: str, evalue: str, traceback: List[str]) -> str:
        """Format an error from IPython into a readable string.

        Args:
            ename: Exception name
            evalue: Exception value
            traceback: List of traceback lines from IPython

        Returns:
            Formatted error string
        """
        # IPython traceback lines often have ANSI color codes, strip them
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        clean_tb = [ansi_escape.sub("", line) for line in traceback]

        # Join traceback and add exception info
        tb_str = "\n".join(clean_tb)
        return f"{tb_str}\n{ename}: {evalue}"

    def get_namespace(self) -> Dict[str, Any]:
        """Get the current namespace of the kernel.

        Returns:
            Dictionary of variable names to values
        """
        if self.kc is None:
            raise RuntimeError("Kernel is not running")

        # Use %who_ls magic to get variable names
        result = self.execute("%who_ls")
        if result.output and "text/plain" in result.output:
            var_names = eval(result.output["text/plain"])

            # Get each variable value
            namespace = {}
            for name in var_names:
                try:
                    # Get repr of variable
                    var_result = self.execute(f"print(repr({name}))")
                    if var_result.stdout:
                        namespace[name] = var_result.stdout.strip()
                except Exception:
                    namespace[name] = "<error getting value>"

            return namespace
        return {}

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
