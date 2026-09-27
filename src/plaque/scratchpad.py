"""Scratchpad execution environment for interactive exploration.

Provides a forked execution environment that allows users and AI agents
to run Python code against the notebook's state without affecting it.

Forking is lazy: the fork starts with a shallow copy of the namespace, and
just before each execution the notebook objects the code refers to are
deep-copied into the fork (see ``isolate_referenced``). Objects too large or
impossible to copy stay shared, and the result carries a warning.
"""

import copy
import re
import time
import types
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from IPython.core.interactiveshell import InteractiveShell

from .environment import Environment, SilentDisplayHook
from .iowrapper import NotebookStdout
from .display import to_renderable
from .api_formatter import to_ms
import sys
from contextlib import redirect_stdout, redirect_stderr


# Objects above this estimated size are shared rather than copied.
DEFAULT_MAX_COPY_BYTES = 256 * 1024 * 1024

# Types whose values can't be mutated in place (or that we deliberately share).
_SHARED_TYPES = (
    int, float, complex, bool, str, bytes, frozenset, range, type(None),
    types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type,
)
_SKIP_NAMES = {"In", "Out", "get_ipython", "exit", "quit"}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _estimated_nbytes(value: Any) -> Optional[int]:
    """Cheap size estimate for array-like objects, or None if unknown."""
    nbytes = getattr(value, "nbytes", None)  # numpy, torch, jax
    if isinstance(nbytes, int):
        return nbytes
    memory_usage = getattr(value, "memory_usage", None)  # pandas
    if callable(memory_usage):
        try:
            usage = memory_usage(deep=False)
            return int(usage.sum()) if hasattr(usage, "sum") else int(usage)
        except Exception:
            return None
    return None


def isolate_referenced(
    code: str,
    namespace: dict,
    source_namespace: dict,
    max_copy_bytes: int = DEFAULT_MAX_COPY_BYTES,
) -> List[str]:
    """Deep-copy notebook objects that ``code`` may touch into ``namespace``.

    A name is copied only while it still refers to the very same object as in
    ``source_namespace``; once copied (or rebound by the user) it is left alone,
    so persistent sessions pay the cost at most once per name. Any identifier
    in the code counts as a reference (over-approximating is only extra
    copying), which also covers magics like ``%timeit f(x)`` and ``!echo $x``.

    Returns warnings for objects that had to stay shared with the notebook.
    """
    warnings = []
    for name in sorted(set(_IDENTIFIER.findall(code))):
        if name.startswith("_") or name in _SKIP_NAMES:
            continue
        if name not in namespace or name not in source_namespace:
            continue
        value = namespace[name]
        if value is not source_namespace[name] or isinstance(value, _SHARED_TYPES):
            continue

        nbytes = _estimated_nbytes(value)
        if nbytes is not None and nbytes > max_copy_bytes:
            warnings.append(
                f"'{name}' ({nbytes / 2**20:.0f} MB) is shared with the notebook, "
                "not copied: in-place changes to it will affect the notebook."
            )
            continue
        try:
            namespace[name] = copy.deepcopy(value)
        except Exception as e:
            warnings.append(
                f"'{name}' could not be copied ({type(e).__name__}) and is shared "
                "with the notebook: in-place changes to it will affect the notebook."
            )
    return warnings


@dataclass
class ExecutionResult:
    """Result of executing code in a scratchpad session."""

    success: bool
    counter: int
    stdout: str
    stderr: str
    result: Any  # The raw result object (will be formatted by api_formatter)
    error: Optional[str]
    execution_time_ms: float
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary (result formatting done separately)."""
        return {
            "success": self.success,
            "counter": self.counter,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "warnings": self.warnings,
            # Note: 'result' is formatted separately by the API layer
        }


@dataclass
class ScratchpadSession:
    """A persistent scratchpad session with its own forked environment."""

    session_id: str
    environment: Environment
    created_at: float
    forked_from_update: float
    execution_count: int = 0
    last_execution: Optional[float] = None
    history: List[tuple] = field(default_factory=list)  # (code, result) pairs
    # The notebook namespace this session was forked from (for lazy copying)
    source_namespace: Optional[dict] = None
    max_copy_bytes: int = DEFAULT_MAX_COPY_BYTES

    def execute(self, code: str) -> ExecutionResult:
        """Execute code in this session's forked environment."""
        start_time = time.time()

        # Create buffers for output capture
        stdout_buffer = NotebookStdout(sys.stdout)
        stderr_buffer = NotebookStdout(sys.stderr)

        # Reset display hook
        self.environment.display_hook.reset_capture()

        warnings = []
        if self.source_namespace is not None:
            warnings = isolate_referenced(
                code,
                self.environment.shell.user_ns,
                self.source_namespace,
                self.max_copy_bytes,
            )

        result = None
        error = None
        stdout = ""
        stderr = ""

        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # Execute using IPython
                exec_result = self.environment.shell.run_cell(
                    code,
                    store_history=False,
                    silent=False,
                )

                stdout = stdout_buffer.getvalue()
                stderr = stderr_buffer.getvalue()

                # Check for errors
                if exec_result.error_before_exec:
                    error = self.environment._format_error(exec_result.error_before_exec)
                elif exec_result.error_in_exec:
                    error = self.environment._format_error(exec_result.error_in_exec)
                else:
                    # Get the result
                    result = exec_result.result
                    if result is None:
                        result = self.environment.display_hook.captured_result

                    # Convert to renderable if we have a result
                    if result is not None:
                        result = to_renderable(result)

        except Exception as e:
            stdout = stdout_buffer.getvalue()
            stderr = stderr_buffer.getvalue()
            error = self.environment._format_error(e)
        finally:
            stdout_buffer.close()
            stderr_buffer.close()

        self.execution_count += 1
        self.last_execution = time.time()
        execution_time_ms = (self.last_execution - start_time) * 1000

        exec_result = ExecutionResult(
            success=error is None,
            counter=self.execution_count,
            stdout=stdout,
            stderr=stderr,
            result=result,
            error=error,
            execution_time_ms=execution_time_ms,
            warnings=warnings,
        )

        # Store in history
        self.history.append((code, exec_result))

        return exec_result

    def get_variables(self, main_namespace: dict) -> List[Dict[str, Any]]:
        """List variables with type info, indicating which came from notebook."""
        variables = []
        for name, value in self.environment.shell.user_ns.items():
            # Skip private/magic variables
            if name.startswith("_") or name in ("In", "Out", "get_ipython", "exit", "quit"):
                continue

            # Check if this variable exists in the main namespace
            from_notebook = name in main_namespace

            try:
                type_name = type(value).__name__
            except Exception:
                type_name = "unknown"

            variables.append({
                "name": name,
                "type": type_name,
                "from_notebook": from_notebook,
            })

        return sorted(variables, key=lambda x: x["name"])

    def reset(self, main_environment: Environment, last_update: float):
        """Re-fork from the main environment, discarding scratchpad state."""
        # Clear the current namespace except builtins
        self.environment.shell.user_ns.clear()

        # Copy from main environment
        self.environment.shell.user_ns.update(main_environment.shell.user_ns.copy())
        self.environment.shell.user_ns["__name__"] = "__main__"

        # Reset state
        self.source_namespace = main_environment.shell.user_ns
        self.forked_from_update = last_update
        self.execution_count = 0
        self.environment.counter = 0
        self.history.clear()


def create_forked_environment(main_environment: Environment) -> Environment:
    """Create a new Environment that starts with a copy of main_environment's namespace.

    The forked environment:
    - Has its own IPython shell instance (isolated execution)
    - Starts with a shallow copy of the main namespace (can read variables)
    - New assignments stay in the fork (don't affect main)

    The copy is shallow; sessions deep-copy objects lazily on first reference
    (see ``isolate_referenced``) so in-place mutation doesn't reach the notebook.
    """
    forked = Environment()

    # Copy the namespace (shallow copy is sufficient for inspection)
    forked.shell.user_ns.update(main_environment.shell.user_ns.copy())

    # Ensure __name__ is set
    forked.shell.user_ns["__name__"] = "__main__"

    # Start counter at 0 for scratchpad
    forked.counter = 0

    return forked


class ScratchpadManager:
    """Manages scratchpad sessions for a notebook."""

    def __init__(
        self,
        main_environment: Environment,
        last_update_fn=None,
        max_copy_bytes: int = DEFAULT_MAX_COPY_BYTES,
    ):
        """Initialize the scratchpad manager.

        Args:
            main_environment: The main notebook's execution environment
            last_update_fn: Optional callable that returns the last update timestamp
            max_copy_bytes: Objects estimated larger than this are shared with
                the notebook instead of copied
        """
        self.main_environment = main_environment
        self.max_copy_bytes = max_copy_bytes
        self.last_update_fn = last_update_fn or (lambda: time.time())
        self.sessions: Dict[str, ScratchpadSession] = {}
        self.max_sessions = 10  # Limit concurrent sessions
        self.session_timeout = 3600  # 1 hour in seconds

    def create_session(self) -> ScratchpadSession:
        """Create a new forked session."""
        # Clean up expired sessions first
        self.cleanup_expired()

        # Check session limit
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest session
            oldest_id = min(
                self.sessions.keys(),
                key=lambda k: self.sessions[k].last_execution or self.sessions[k].created_at
            )
            del self.sessions[oldest_id]

        session_id = f"sp_{uuid.uuid4().hex[:12]}"
        forked_env = create_forked_environment(self.main_environment)
        last_update = self.last_update_fn()

        session = ScratchpadSession(
            session_id=session_id,
            environment=forked_env,
            created_at=time.time(),
            forked_from_update=last_update,
            source_namespace=self.main_environment.shell.user_ns,
            max_copy_bytes=self.max_copy_bytes,
        )

        self.sessions[session_id] = session
        return session

    def execute_ephemeral(self, code: str) -> ExecutionResult:
        """Execute code in a fresh fork that's immediately discarded.

        This is the simplest mode - create a fork, run the code, return the result,
        discard the fork. No persistent state.
        """
        forked_env = create_forked_environment(self.main_environment)

        # Create a temporary session just for execution
        temp_session = ScratchpadSession(
            session_id="ephemeral",
            environment=forked_env,
            created_at=time.time(),
            forked_from_update=self.last_update_fn(),
            source_namespace=self.main_environment.shell.user_ns,
            max_copy_bytes=self.max_copy_bytes,
        )

        return temp_session.execute(code)

    def get_session(self, session_id: str) -> Optional[ScratchpadSession]:
        """Get a session by ID, or None if not found or expired."""
        session = self.sessions.get(session_id)
        if session is None:
            return None

        # Check if expired
        last_activity = session.last_execution or session.created_at
        if time.time() - last_activity > self.session_timeout:
            del self.sessions[session_id]
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if session existed."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        self.cleanup_expired()

        return [
            {
                "session_id": session.session_id,
                "created_at": to_ms(session.created_at),
                "execution_count": session.execution_count,
                "last_execution": to_ms(session.last_execution),
            }
            for session in self.sessions.values()
        ]

    def cleanup_expired(self):
        """Remove sessions older than the timeout."""
        now = time.time()
        expired = [
            session_id
            for session_id, session in self.sessions.items()
            if now - (session.last_execution or session.created_at) > self.session_timeout
        ]
        for session_id in expired:
            del self.sessions[session_id]
