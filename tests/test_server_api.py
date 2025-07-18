"""Tests for the server API endpoints."""

import json
import tempfile
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from plaque.cell import Cell, CellType
from plaque.server import NotebookHTTPServer
from plaque.processor import Processor
from plaque.renderables import HTML, PNG


class TestServerAPI:
    """Test the API endpoints of the notebook server."""

    @pytest.fixture
    def mock_processor(self):
        """Create a mock processor with test cells."""
        processor = Mock(spec=Processor)
        processor.cells = [
            Cell(type=CellType.MARKDOWN, content="# Test Notebook", lineno=1),
            Cell(
                type=CellType.CODE,
                content="x = 42",
                lineno=3,
                counter=1,
                result=42,
                provides={"x"},
            ),
            Cell(
                type=CellType.CODE,
                content="y = x * 2",
                lineno=5,
                counter=2,
                result=84,
                stdout="",
                provides={"y"},
                requires={"x"},
                depends_on={1},
            ),
            Cell(
                type=CellType.CODE,
                content="1/0",
                lineno=7,
                counter=3,
                error="ZeroDivisionError: division by zero",
            ),
            Cell(
                type=CellType.CODE,
                content="z = 100",
                lineno=9,
                counter=0,  # Not executed yet
            ),
        ]
        return processor

    @pytest.fixture
    def server_url(self, mock_processor):
        """Start a test server and return its URL."""
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            notebook_path = Path(f.name)

            # Find an available port
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                port = s.getsockname()[1]

            server = NotebookHTTPServer(notebook_path, port=port, bind="localhost")
            server.processor = mock_processor
            server.current_cells = mock_processor.cells

            # Mock the regenerate callback
            def mock_regenerate(path, image_dir):
                return "<html><body>Test</body></html>"

            # Start server in a thread
            server_thread = threading.Thread(
                target=server.start,
                args=(mock_regenerate, False, mock_processor),
                daemon=True,
            )

            # Patch the file watcher to avoid actual file watching
            with patch("plaque.server.FileWatcher"):
                server_thread.start()
                time.sleep(0.5)  # Give server time to start

                yield f"http://localhost:{port}"

                # Server will stop when thread dies

    def make_request(self, url: str) -> dict:
        """Make a GET request and return JSON response."""
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_content = e.read().decode("utf-8")
            return json.loads(error_content)

    def test_api_cells_list(self, server_url):
        """Test the /api/cells endpoint."""
        response = self.make_request(f"{server_url}/api/cells")

        assert "cells" in response
        cells = response["cells"]
        assert len(cells) == 5

        # Check first cell (markdown)
        assert cells[0]["index"] == 0
        assert cells[0]["type"] == "markdown"
        assert cells[0]["is_code"] is False
        assert cells[0]["has_error"] is False
        assert cells[0]["execution_count"] is None

        # Check second cell (code)
        assert cells[1]["index"] == 1
        assert cells[1]["type"] == "code"
        assert cells[1]["is_code"] is True
        assert cells[1]["has_error"] is False
        assert cells[1]["execution_count"] == 1

        # Check error cell
        assert cells[3]["has_error"] is True
        assert cells[3]["execution_count"] == 3

    def test_api_cell_detail(self, server_url):
        """Test the /api/cell/{index} endpoint."""
        # Test successful code cell
        response = self.make_request(f"{server_url}/api/cell/1")

        assert response["index"] == 1
        assert response["type"] == "code"
        assert response["content"] == "x = 42"
        assert response["execution"]["status"] == "success"
        assert response["execution"]["counter"] == 1
        assert response["execution"]["result"]["type"] == "text/plain"
        assert response["execution"]["result"]["data"] == "42"
        assert response["dependencies"]["provides"] == ["x"]

        # Test markdown cell
        response = self.make_request(f"{server_url}/api/cell/0")
        assert response["type"] == "markdown"
        assert "execution" not in response

        # Test error cell
        response = self.make_request(f"{server_url}/api/cell/3")
        assert response["execution"]["status"] == "error"
        assert response["execution"]["error"] == "ZeroDivisionError: division by zero"

    def test_api_cell_input(self, server_url):
        """Test the /api/cell/{index}/input endpoint."""
        response = self.make_request(f"{server_url}/api/cell/1/input")

        assert response["index"] == 1
        assert response["content"] == "x = 42"
        assert len(response) == 2  # Only index and content

    def test_api_cell_output(self, server_url):
        """Test the /api/cell/{index}/output endpoint."""
        response = self.make_request(f"{server_url}/api/cell/1/output")

        assert response["index"] == 1
        assert response["counter"] == 1
        assert response["error"] is None
        assert response["result"]["type"] == "text/plain"
        assert response["result"]["data"] == "42"

    def test_api_notebook_state(self, server_url):
        """Test the /api/notebook/state endpoint."""
        response = self.make_request(f"{server_url}/api/notebook/state")

        assert response["total_cells"] == 5
        assert response["code_cells"] == 4
        assert response["markdown_cells"] == 1
        assert response["executed_cells"] == 3
        assert response["error_cells"] == 1
        assert response["cells_with_errors"] == [3]
        assert "last_update" in response

    def test_api_search(self, server_url):
        """Test the /api/search endpoint."""
        # Search for 'x'
        response = self.make_request(f"{server_url}/api/search?q=x")

        assert response["query"] == "x"
        assert len(response["results"]) == 2  # cells 1 and 2 contain 'x'

        result = response["results"][0]
        assert result["index"] == 1
        assert result["type"] == "code"
        assert "preview" in result

        # Search with no query
        try:
            response = self.make_request(f"{server_url}/api/search")
            assert "error" in response
        except urllib.error.HTTPError:
            pass  # Expected

    def test_api_invalid_endpoints(self, server_url):
        """Test error handling for invalid endpoints."""
        # Invalid cell index
        try:
            response = self.make_request(f"{server_url}/api/cell/999")
            assert "error" in response
        except urllib.error.HTTPError as e:
            assert e.code == 404

        # Invalid endpoint
        try:
            response = self.make_request(f"{server_url}/api/invalid")
            assert "error" in response
        except urllib.error.HTTPError as e:
            assert e.code == 404

    def test_api_cors_headers(self, server_url):
        """Test that CORS headers are present."""
        req = urllib.request.Request(f"{server_url}/api/cells")
        with urllib.request.urlopen(req) as response:
            headers = response.headers
            assert headers.get("Access-Control-Allow-Origin") == "*"
            assert "GET" in headers.get("Access-Control-Allow-Methods", "")


class TestAPIFormatterIntegration:
    """Test the API formatter with different result types."""

    def test_format_result_with_renderables(self):
        """Test formatting various renderable types."""

        # Test HTML result
        html_cell = Cell(
            type=CellType.CODE,
            content="HTML('<b>Bold</b>')",
            lineno=1,
            counter=1,
            result=HTML("<b>Bold</b>"),
        )
        from plaque.api_formatter import cell_to_json

        result = cell_to_json(html_cell, 0)
        assert result["execution"]["result"]["type"] == "text/html"
        assert result["execution"]["result"]["data"] == "<b>Bold</b>"

        # Test PNG result (without image dir)
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        png_cell = Cell(
            type=CellType.CODE,
            content="show_image()",
            lineno=1,
            counter=1,
            result=PNG(png_data),
        )
        result = cell_to_json(png_cell, 0)
        assert result["execution"]["result"]["type"] == "image/png"
        assert "data" in result["execution"]["result"]
        assert "url" not in result["execution"]["result"]

    def test_format_dataframe_result(self):
        """Test formatting pandas DataFrame results."""

        # Create a mock DataFrame that properly mimics pandas
        class MockDataFrame:
            def __init__(self):
                self.shape = (3, 2)
                self.columns = ["A", "B"]

            def to_dict(self, orient="records"):
                return [{"A": 1, "B": 4}, {"A": 2, "B": 5}, {"A": 3, "B": 6}]

        # Set the class name properly
        MockDataFrame.__name__ = "DataFrame"

        df_cell = Cell(
            type=CellType.CODE,
            content="df",
            lineno=1,
            counter=1,
            result=MockDataFrame(),
        )

        from plaque.api_formatter import cell_to_json

        result = cell_to_json(df_cell, 0)

        df_result = result["execution"]["result"]
        assert df_result["type"] == "dataframe"
        assert df_result["shape"] == [3, 2]
        assert df_result["columns"] == ["A", "B"]
        assert len(df_result["data"]) == 3


class TestAPIEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_cells_list(self):
        """Test with no cells."""
        from plaque.api_formatter import cells_to_json, notebook_state_to_json

        cells = []
        result = cells_to_json(cells)
        assert result == []

        state = notebook_state_to_json(cells, time.time())
        assert state["total_cells"] == 0
        assert state["code_cells"] == 0
        assert state["cells_with_errors"] == []

    def test_f_string_markdown_cell(self):
        """Test f-string markdown cells."""
        from plaque.api_formatter import cell_to_json

        # F-string markdown with result
        cell = Cell(
            type=CellType.MARKDOWN,
            content='f"Value: {x}"',
            lineno=1,
            metadata={"string_prefix": "f"},
            counter=1,
            result="Value: 42",
        )

        result = cell_to_json(cell, 0)
        assert result["type"] == "markdown"
        assert "execution" in result  # F-string markdown cells have execution
        assert result["execution"]["status"] == "success"
        assert result["execution"]["result"]["data"] == "Value: 42"

        # F-string markdown with error
        error_cell = Cell(
            type=CellType.MARKDOWN,
            content='f"Value: {undefined}"',
            lineno=1,
            metadata={"string_prefix": "f"},
            counter=1,
            error="NameError: name 'undefined' is not defined",
        )

        result = cell_to_json(error_cell, 0)
        assert result["execution"]["status"] == "error"
        assert (
            result["execution"]["error"] == "NameError: name 'undefined' is not defined"
        )
