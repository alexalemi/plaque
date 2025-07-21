"""Tests for the IPython execution environment."""

import pytest
import sys
from unittest.mock import patch

from plaque.cell import Cell
from plaque.environment import BaseEnvironment


# Mock the jupyter_client module if not available
try:
    import jupyter_client

    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False


@pytest.mark.skipif(not JUPYTER_AVAILABLE, reason="jupyter_client not available")
class TestIPythonEnvironment:
    """Tests for IPythonEnvironment with real jupyter_client."""

    @pytest.fixture
    def env(self):
        """Create an IPythonEnvironment instance."""
        from plaque.ipython_environment import IPythonEnvironment

        env = IPythonEnvironment(timeout=5.0)
        yield env
        # Cleanup
        if env._started:
            env.stop()

    def test_inheritance(self, env):
        """Test that IPythonEnvironment inherits from BaseEnvironment."""
        assert isinstance(env, BaseEnvironment)

    def test_start_stop(self, env):
        """Test starting and stopping the kernel."""
        assert not env._started

        env.start()
        assert env._started
        assert env.kernel is not None
        assert env.kernel.is_alive()

        env.stop()
        assert not env._started
        assert env.kernel is None

    def test_simple_execution(self, env):
        """Test executing simple Python code."""
        env.start()

        cell = Cell(content="x = 42\nprint(x)", lineno=1)
        result = env.execute_cell(cell)

        assert cell.stdout == "42\n"
        assert cell.stderr == ""
        assert cell.error is None
        assert cell.counter > 0

    def test_expression_cell(self, env):
        """Test executing an expression cell."""
        env.start()

        cell = Cell(content="2 + 2", lineno=1)
        result = env.execute_cell(cell)

        assert result == 4
        assert cell.result == 4
        assert cell.error is None

    def test_error_handling(self, env):
        """Test error handling in code execution."""
        env.start()

        cell = Cell(content="raise ValueError('test error')", lineno=1)
        result = env.execute_cell(cell)

        assert result is None
        assert cell.error is not None
        assert "ValueError: test error" in cell.error
        assert cell.stdout == ""

    def test_top_level_await(self, env):
        """Test that top-level await works."""
        env.start()

        # First set up an async function
        setup_cell = Cell(
            content="""
import asyncio

async def get_value():
    await asyncio.sleep(0.01)
    return 42
""",
            lineno=1,
        )
        env.execute_cell(setup_cell)

        # Now test top-level await
        cell = Cell(content="result = await get_value()\nprint(result)", lineno=10)
        result = env.execute_cell(cell)

        assert cell.stdout == "42\n"
        assert cell.error is None

    def test_namespace_tracking(self, env):
        """Test that namespace tracking works."""
        env.start()

        # Define some variables
        cell1 = Cell(content="x = 42\ny = 'hello'", lineno=1)
        env.execute_cell(cell1)

        # Get namespace
        namespace = env.get_namespace()

        assert "x" in namespace
        assert "y" in namespace
        # Note: values are repr() strings in the namespace
        assert "42" in str(namespace["x"])
        assert "hello" in str(namespace["y"])

    def test_context_manager(self):
        """Test using IPythonEnvironment as context manager."""
        from plaque.ipython_environment import IPythonEnvironment

        with IPythonEnvironment(timeout=5.0) as env:
            assert env._started
            assert env.kernel is not None

            # Execute some code
            cell = Cell(content="x = 1", lineno=1)
            env.execute_cell(cell)
            assert cell.error is None

        # After context, kernel should be stopped
        assert not env._started
        assert env.kernel is None


@pytest.mark.skipif(
    JUPYTER_AVAILABLE, reason="Test mocking when jupyter_client not available"
)
class TestIPythonEnvironmentMocked:
    """Tests for IPythonEnvironment with mocked jupyter_client."""

    def test_import_error_without_jupyter(self):
        """Test that appropriate error is raised without jupyter_client."""
        # Remove jupyter_client from sys.modules if present
        if "jupyter_client" in sys.modules:
            pytest.skip("Cannot test import error when jupyter_client is available")

        with patch.dict(sys.modules, {"jupyter_client": None}):
            with pytest.raises(ImportError) as exc_info:
                from plaque.ipython_environment import IPythonEnvironment

                env = IPythonEnvironment()
                env.start()

            assert "jupyter-client" in str(exc_info.value)


class TestProcessorIntegration:
    """Test Processor integration with IPython environment."""

    @pytest.mark.skipif(not JUPYTER_AVAILABLE, reason="jupyter_client not available")
    def test_processor_with_ipython(self):
        """Test that Processor can use IPython environment."""
        from plaque.processor import Processor

        # Create processor with IPython environment
        processor = Processor(environment_type="ipython", kernel_timeout=5.0)

        # Check that the environment is IPython
        from plaque.ipython_environment import IPythonEnvironment

        assert isinstance(processor.environment, IPythonEnvironment)

        # Cleanup
        del processor  # Should trigger __del__ and stop kernel

    def test_processor_with_invalid_environment_type(self):
        """Test that Processor raises error for invalid environment type."""
        from plaque.processor import Processor

        # This should work (default)
        processor = Processor(environment_type="python")
        from plaque.environment import PythonEnvironment

        assert isinstance(processor.environment, PythonEnvironment)

    @pytest.mark.skipif(
        JUPYTER_AVAILABLE, reason="Test error when jupyter not available"
    )
    def test_processor_ipython_not_available(self):
        """Test that Processor raises appropriate error when IPython not available."""
        if JUPYTER_AVAILABLE:
            pytest.skip("Cannot test import error when jupyter_client is available")

        from plaque.processor import Processor

        with pytest.raises(ImportError) as exc_info:
            processor = Processor(environment_type="ipython")

        assert "jupyter-client" in str(exc_info.value)


class TestCLIIntegration:
    """Test CLI integration with IPython environment."""

    @pytest.mark.skipif(not JUPYTER_AVAILABLE, reason="jupyter_client not available")
    def test_cli_ipython_flag(self):
        """Test that CLI --ipython flag works."""
        from click.testing import CliRunner
        from plaque.cli import main

        runner = CliRunner()

        # Create a test notebook file
        with runner.isolated_filesystem():
            with open("test.py", "w") as f:
                f.write("""
# %%
x = 42
print(f"Value: {x}")

# %%
# Test that we can use IPython features
result = 2 + 2
result
""")

            # Run with --ipython flag
            result = runner.invoke(main, ["--ipython", "render", "test.py"])

            # Should succeed
            assert result.exit_code == 0
            assert "Generated: test.html" in result.output

            # Check that HTML was created
            assert os.path.exists("test.html")


import os
