"""Tests for the scratchpad functionality."""

import pytest
import time

from src.plaque.scratchpad import (
    ScratchpadSession,
    ScratchpadManager,
    ExecutionResult,
    create_forked_environment,
)
from src.plaque.environment import Environment


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ExecutionResult(
            success=True,
            counter=1,
            stdout="hello\n",
            stderr="",
            result=42,
            error=None,
            execution_time_ms=10.5,
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["counter"] == 1
        assert d["stdout"] == "hello\n"
        assert d["stderr"] == ""
        assert d["error"] is None
        assert d["execution_time_ms"] == 10.5
        # Note: result is not included, it's formatted separately

    def test_to_dict_with_error(self):
        """Test conversion with error."""
        result = ExecutionResult(
            success=False,
            counter=1,
            stdout="",
            stderr="",
            result=None,
            error="ZeroDivisionError: division by zero",
            execution_time_ms=5.0,
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["error"] == "ZeroDivisionError: division by zero"


class TestCreateForkedEnvironment:
    """Test environment forking."""

    def test_basic_fork(self):
        """Test that forking creates an independent environment."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 42

        forked = create_forked_environment(main_env)

        # Forked env should have the variable
        assert forked.shell.user_ns.get("x") == 42
        # Forked env should be independent
        assert forked.shell is not main_env.shell

    def test_fork_isolation_new_variables(self):
        """Test that new variables in fork don't affect main."""
        main_env = Environment()
        main_env.shell.user_ns["original"] = 100

        forked = create_forked_environment(main_env)
        forked.shell.user_ns["new_var"] = 999

        # Main should not have the new variable
        assert "new_var" not in main_env.shell.user_ns
        # Forked should have both
        assert forked.shell.user_ns.get("original") == 100
        assert forked.shell.user_ns.get("new_var") == 999

    def test_fork_isolation_overwrite(self):
        """Test that overwriting variables in fork doesn't affect main."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 10

        forked = create_forked_environment(main_env)
        forked.shell.user_ns["x"] = 999

        # Main should still have original value
        assert main_env.shell.user_ns.get("x") == 10
        # Forked should have new value
        assert forked.shell.user_ns.get("x") == 999

    def test_fork_counter_reset(self):
        """Test that forked environment starts with counter at 0."""
        main_env = Environment()
        main_env.counter = 50

        forked = create_forked_environment(main_env)

        assert forked.counter == 0

    def test_fork_preserves_name(self):
        """Test that __name__ is set correctly."""
        main_env = Environment()

        forked = create_forked_environment(main_env)

        assert forked.shell.user_ns["__name__"] == "__main__"


class TestScratchpadSession:
    """Test ScratchpadSession execution."""

    def test_simple_execution(self):
        """Test executing simple code."""
        main_env = Environment()
        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        result = session.execute("2 + 3")

        assert result.success is True
        assert result.error is None
        assert result.execution_time_ms > 0

    def test_execution_with_variable_access(self):
        """Test accessing variables from main environment."""
        main_env = Environment()
        main_env.shell.user_ns["data"] = [1, 2, 3, 4, 5]

        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        result = session.execute("len(data)")

        assert result.success is True
        assert result.error is None

    def test_execution_with_stdout(self):
        """Test capturing stdout."""
        main_env = Environment()
        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        result = session.execute('print("Hello")')

        assert result.success is True
        assert result.stdout == "Hello\n"

    def test_execution_with_error(self):
        """Test handling errors."""
        main_env = Environment()
        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        result = session.execute("1 / 0")

        assert result.success is False
        assert result.error is not None
        assert "ZeroDivisionError" in result.error

    def test_execution_count_increments(self):
        """Test that execution count increments."""
        main_env = Environment()
        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        assert session.execution_count == 0

        session.execute("1 + 1")
        assert session.execution_count == 1

        session.execute("2 + 2")
        assert session.execution_count == 2

    def test_history_tracking(self):
        """Test that execution history is tracked."""
        main_env = Environment()
        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        session.execute("x = 1")
        session.execute("x + 1")

        assert len(session.history) == 2
        assert session.history[0][0] == "x = 1"
        assert session.history[1][0] == "x + 1"

    def test_isolation_from_main(self):
        """Test that scratchpad doesn't affect main namespace."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 10

        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        session.execute("x = 999")
        session.execute("new_var = 123")

        # Main should be unaffected
        assert main_env.shell.user_ns.get("x") == 10
        assert "new_var" not in main_env.shell.user_ns

    def test_get_variables(self):
        """Test listing variables."""
        main_env = Environment()
        main_env.shell.user_ns["from_main"] = 42

        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        session.execute("local_var = 100")

        variables = session.get_variables(main_env.shell.user_ns)

        # Find the variables we care about
        var_dict = {v["name"]: v for v in variables}

        assert "from_main" in var_dict
        assert var_dict["from_main"]["from_notebook"] is True

        assert "local_var" in var_dict
        assert var_dict["local_var"]["from_notebook"] is False

    def test_reset(self):
        """Test resetting a session."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 10

        session = ScratchpadSession(
            session_id="test",
            environment=create_forked_environment(main_env),
            created_at=time.time(),
            forked_from_update=time.time(),
        )

        # Make some changes
        session.execute("x = 999")
        session.execute("y = 123")
        assert session.execution_count == 2

        # Update main and reset
        main_env.shell.user_ns["x"] = 20
        session.reset(main_env, time.time())

        # Session should be refreshed
        assert session.execution_count == 0
        assert len(session.history) == 0
        assert session.environment.shell.user_ns.get("x") == 20
        assert "y" not in session.environment.shell.user_ns


class TestScratchpadManager:
    """Test ScratchpadManager."""

    def test_create_session(self):
        """Test creating a new session."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        session = manager.create_session()

        assert session is not None
        assert session.session_id.startswith("sp_")
        assert session.session_id in manager.sessions

    def test_execute_ephemeral(self):
        """Test ephemeral execution."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 42
        manager = ScratchpadManager(main_env)

        result = manager.execute_ephemeral("x * 2")

        assert result.success is True
        # No persistent session should be created
        assert len(manager.sessions) == 0

    def test_execute_ephemeral_isolation(self):
        """Test that ephemeral execution doesn't affect main."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = 10
        manager = ScratchpadManager(main_env)

        manager.execute_ephemeral("x = 999")

        # Main should be unaffected
        assert main_env.shell.user_ns.get("x") == 10

    def test_get_session(self):
        """Test retrieving a session."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        created = manager.create_session()
        retrieved = manager.get_session(created.session_id)

        assert retrieved is created

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        result = manager.get_session("nonexistent")

        assert result is None

    def test_delete_session(self):
        """Test deleting a session."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        session = manager.create_session()
        session_id = session.session_id

        result = manager.delete_session(session_id)

        assert result is True
        assert session_id not in manager.sessions

    def test_delete_nonexistent_session(self):
        """Test deleting non-existent session returns False."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        result = manager.delete_session("nonexistent")

        assert result is False

    def test_list_sessions(self):
        """Test listing sessions."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)

        session1 = manager.create_session()
        session2 = manager.create_session()

        sessions = manager.list_sessions()

        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_max_sessions_limit(self):
        """Test that max sessions limit is enforced."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)
        manager.max_sessions = 3

        # Create more sessions than limit
        sessions = [manager.create_session() for _ in range(5)]

        # Should only keep max_sessions
        assert len(manager.sessions) == 3

    def test_session_timeout(self):
        """Test that expired sessions are cleaned up."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)
        manager.session_timeout = 0.1  # 100ms timeout

        session = manager.create_session()
        session_id = session.session_id

        # Session should exist
        assert manager.get_session(session_id) is not None

        # Wait for timeout
        time.sleep(0.15)

        # Session should be gone
        assert manager.get_session(session_id) is None

    def test_cleanup_expired(self):
        """Test cleanup of expired sessions."""
        main_env = Environment()
        manager = ScratchpadManager(main_env)
        manager.session_timeout = 0.1

        session1 = manager.create_session()
        time.sleep(0.15)
        session2 = manager.create_session()

        manager.cleanup_expired()

        # session1 should be gone, session2 should remain
        assert session1.session_id not in manager.sessions
        assert session2.session_id in manager.sessions


class TestIntegrationScenarios:
    """Integration tests for common scratchpad use cases."""

    def test_inspect_dataframe_shape(self):
        """Test typical use case: inspecting DataFrame shape."""
        main_env = Environment()

        # Simulate a notebook that has a DataFrame
        main_env.shell.user_ns["df"] = type("MockDF", (), {
            "shape": (100, 5),
            "columns": ["a", "b", "c", "d", "e"]
        })()

        manager = ScratchpadManager(main_env)
        result = manager.execute_ephemeral("df.shape")

        assert result.success is True

    def test_inspect_variable_type(self):
        """Test inspecting variable type."""
        main_env = Environment()
        main_env.shell.user_ns["x"] = [1, 2, 3]

        manager = ScratchpadManager(main_env)
        result = manager.execute_ephemeral("type(x).__name__")

        assert result.success is True

    def test_multiple_inspections_in_session(self):
        """Test running multiple inspections in a persistent session."""
        main_env = Environment()
        main_env.shell.user_ns["data"] = {"a": 1, "b": 2, "c": 3}

        manager = ScratchpadManager(main_env)
        session = manager.create_session()

        # Run multiple inspections
        r1 = session.execute("len(data)")
        r2 = session.execute("list(data.keys())")
        r3 = session.execute("sum(data.values())")

        assert r1.success is True
        assert r2.success is True
        assert r3.success is True

    def test_build_up_state_in_session(self):
        """Test building up state across multiple executions."""
        main_env = Environment()
        main_env.shell.user_ns["raw_data"] = [1, 2, 3, 4, 5]

        manager = ScratchpadManager(main_env)
        session = manager.create_session()

        # Build up analysis state
        session.execute("filtered = [x for x in raw_data if x > 2]")
        session.execute("total = sum(filtered)")
        result = session.execute("total / len(filtered)")

        assert result.success is True
        # Main namespace should be unchanged
        assert "filtered" not in main_env.shell.user_ns
        assert "total" not in main_env.shell.user_ns
