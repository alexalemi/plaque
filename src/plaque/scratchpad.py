"""Scratchpad execution environment for interactive exploration.

Provides a forked execution environment that allows users and AI agents
to run Python code against the notebook's state without affecting it.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from IPython.core.interactiveshell import InteractiveShell

from .environment import Environment, SilentDisplayHook
from .iowrapper import NotebookStdout
from .display import to_renderable
import sys
from contextlib import redirect_stdout, redirect_stderr


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary (result formatting done separately)."""
        return {
            "success": self.success,
            "counter": self.counter,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
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

    def execute(self, code: str) -> ExecutionResult:
        """Execute code in this session's forked environment."""
        start_time = time.time()

        # Create buffers for output capture
        stdout_buffer = NotebookStdout(sys.stdout)
        stderr_buffer = NotebookStdout(sys.stderr)

        # Reset display hook
        self.environment.display_hook.reset_capture()

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
    - Shared mutable objects can be read (mutations would propagate, but that's
      acceptable for the inspection use case)
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

    def __init__(self, main_environment: Environment, last_update_fn=None):
        """Initialize the scratchpad manager.

        Args:
            main_environment: The main notebook's execution environment
            last_update_fn: Optional callable that returns the last update timestamp
        """
        self.main_environment = main_environment
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
                "created_at": session.created_at,
                "execution_count": session.execution_count,
                "last_execution": session.last_execution,
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
