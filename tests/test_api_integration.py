"""Integration test demonstrating agent API usage."""

import json
import tempfile
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path


class TestAPIIntegration:
    """Integration test for the API with a real server."""

    def test_agent_workflow(self):
        """Test a typical agent workflow with the API."""
        # Create a test notebook
        notebook_content = """# %% [markdown]
# # API Test Notebook
# Testing the agent API endpoints

# %%
x = 42
print(f"x = {x}")

# %%
y = x * 2
print(f"y = {y}")

# %%
# This will error
result = 1 / 0

# %%
# This depends on x and y
total = x + y
print(f"Total: {total}")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(notebook_content)
            notebook_path = f.name

        # Start server in subprocess
        port = 5555
        proc = subprocess.Popen(
            ["uv", "run", "plaque", "serve", notebook_path, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for server to start
            time.sleep(2)

            base_url = f"http://localhost:{port}"

            # 1. Agent gets notebook overview
            req = urllib.request.Request(f"{base_url}/api/cells")
            with urllib.request.urlopen(req) as response:
                cells = json.loads(response.read().decode("utf-8"))["cells"]

            assert len(cells) == 5
            assert cells[0]["type"] == "markdown"
            assert cells[1]["type"] == "code"

            # 2. Agent checks notebook state
            req = urllib.request.Request(f"{base_url}/api/notebook/state")
            with urllib.request.urlopen(req) as response:
                state = json.loads(response.read().decode("utf-8"))

            assert state["total_cells"] == 5
            assert state["code_cells"] == 4
            assert len(state["cells_with_errors"]) == 1
            assert 3 in state["cells_with_errors"]  # Cell 3 has the division by zero

            # 3. Agent inspects the error cell
            error_index = state["cells_with_errors"][0]
            req = urllib.request.Request(f"{base_url}/api/cell/{error_index}")
            with urllib.request.urlopen(req) as response:
                error_cell = json.loads(response.read().decode("utf-8"))

            assert error_cell["execution"]["status"] == "error"
            assert "ZeroDivisionError" in error_cell["execution"]["error"]

            # 4. Agent searches for dependencies
            req = urllib.request.Request(f"{base_url}/api/search?q=total")
            with urllib.request.urlopen(req) as response:
                search_results = json.loads(response.read().decode("utf-8"))

            assert len(search_results["results"]) >= 1
            assert any(r["index"] == 4 for r in search_results["results"])

            # 5. Agent gets specific cell output
            req = urllib.request.Request(f"{base_url}/api/cell/1/output")
            with urllib.request.urlopen(req) as response:
                output = json.loads(response.read().decode("utf-8"))

            assert output["stdout"] == "x = 42\n"
            assert output["error"] is None

        finally:
            # Clean up
            proc.terminate()
            proc.wait()
            Path(notebook_path).unlink()


if __name__ == "__main__":
    # Run the integration test
    test = TestAPIIntegration()
    test.test_agent_workflow()
    print("Integration test passed!")
