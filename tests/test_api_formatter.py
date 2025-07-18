"""Tests for API formatter functionality."""

import base64
from pathlib import Path
import tempfile


from plaque.cell import Cell, CellType
from plaque.api_formatter import (
    format_result,
    cell_to_json,
    cells_to_json,
    notebook_state_to_json,
)
from plaque.renderables import Text, HTML, PNG, JSON as JSONRenderable


class TestFormatResult:
    """Test result formatting for different data types."""

    def test_format_none(self):
        assert format_result(None) is None

    def test_format_text(self):
        text = Text("Hello world")
        result = format_result(text)
        assert result["type"] == "text/plain"
        assert result["data"] == "Hello world"

    def test_format_html(self):
        html = HTML("<h1>Title</h1>")
        result = format_result(html)
        assert result["type"] == "text/html"
        assert result["data"] == "<h1>Title</h1>"

    def test_format_json(self):
        data = {"key": "value"}
        json_obj = JSONRenderable(data)
        result = format_result(json_obj)
        assert result["type"] == "application/json"
        assert result["data"] == data

    def test_format_png_without_image_dir(self):
        png_data = b"\x89PNG\r\n\x1a\n"  # PNG header
        png = PNG(png_data)
        result = format_result(png)
        assert result["type"] == "image/png"
        assert result["data"] == base64.standard_b64encode(png_data).decode("utf-8")
        assert "url" not in result

    def test_format_png_with_image_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = Path(tmpdir)
            png_data = b"\x89PNG\r\n\x1a\n"
            png = PNG(png_data)
            result = format_result(png, image_dir, cell_counter=1)
            assert result["type"] == "image/png"
            assert "url" in result
            assert result["url"] == "/images/cell_1_img.png"
            assert "data" not in result  # No base64 by default

    def test_format_png_with_base64_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = Path(tmpdir)
            png_data = b"\x89PNG\r\n\x1a\n"
            png = PNG(png_data)
            result = format_result(png, image_dir, cell_counter=2, include_base64=True)
            assert result["type"] == "image/png"
            assert result["url"] == "/images/cell_2_img.png"
            assert result["data"] == base64.standard_b64encode(png_data).decode("utf-8")

    def test_format_plain_object(self):
        obj = {"some": "dict"}
        result = format_result(obj)
        assert result["type"] == "text/plain"
        assert result["data"] == str(obj)


class TestCellToJson:
    """Test cell serialization to JSON."""

    def test_code_cell_success(self):
        cell = Cell(
            type=CellType.CODE, content="x = 42", lineno=1, counter=1, result=42
        )

        result = cell_to_json(cell, 0)
        assert result["index"] == 0
        assert result["type"] == "code"
        assert result["content"] == "x = 42"
        assert result["execution"]["status"] == "success"
        assert result["execution"]["counter"] == 1
        assert result["execution"]["result"]["type"] == "text/plain"
        assert result["execution"]["result"]["data"] == "42"

    def test_code_cell_error(self):
        cell = Cell(
            type=CellType.CODE,
            content="1/0",
            lineno=5,
            counter=1,
            error="ZeroDivisionError: division by zero",
        )

        result = cell_to_json(cell, 2)
        assert result["index"] == 2
        assert result["execution"]["status"] == "error"
        assert result["execution"]["error"] == "ZeroDivisionError: division by zero"
        assert result["execution"]["result"] is None

    def test_code_cell_pending(self):
        cell = Cell(type=CellType.CODE, content="x = 10", lineno=3, counter=0)

        result = cell_to_json(cell, 1)
        assert result["execution"]["status"] == "pending"
        assert result["execution"]["counter"] == 0

    def test_markdown_cell(self):
        cell = Cell(
            type=CellType.MARKDOWN, content="# Hello\nThis is markdown", lineno=10
        )

        result = cell_to_json(cell, 3)
        assert result["type"] == "markdown"
        assert result["content"] == "# Hello\nThis is markdown"
        assert "execution" not in result

    def test_cell_with_dependencies(self):
        cell = Cell(
            type=CellType.CODE,
            content="y = x + 1",
            lineno=2,
            provides={"y"},
            requires={"x"},
            depends_on={0},
        )

        result = cell_to_json(cell, 1)
        assert "dependencies" in result
        assert result["dependencies"]["provides"] == ["y"]
        assert result["dependencies"]["requires"] == ["x"]
        assert result["dependencies"]["depends_on"] == [0]

    def test_cell_with_stdout_stderr(self):
        cell = Cell(
            type=CellType.CODE,
            content="print('hello'); import sys; sys.stderr.write('error')",
            lineno=1,
            counter=1,
            stdout="hello\n",
            stderr="error",
        )

        result = cell_to_json(cell, 0)
        assert result["execution"]["stdout"] == "hello\n"
        assert result["execution"]["stderr"] == "error"


class TestNotebookState:
    """Test notebook state summary."""

    def test_notebook_state(self):
        cells = [
            Cell(type=CellType.MARKDOWN, content="# Title", lineno=1),
            Cell(type=CellType.CODE, content="x = 1", lineno=2, counter=1),
            Cell(type=CellType.CODE, content="y = 2", lineno=3, counter=2),
            Cell(
                type=CellType.CODE,
                content="1/0",
                lineno=4,
                counter=3,
                error="ZeroDivisionError",
            ),
            Cell(type=CellType.CODE, content="z = 3", lineno=5, counter=0),
        ]

        state = notebook_state_to_json(cells, 1234567890.0)

        assert state["total_cells"] == 5
        assert state["code_cells"] == 4
        assert state["markdown_cells"] == 1
        assert state["executed_cells"] == 3
        assert state["error_cells"] == 1
        assert state["last_update"] == 1234567890.0
        assert state["cells_with_errors"] == [3]


class TestCellsToJson:
    """Test batch cell conversion."""

    def test_cells_to_json(self):
        cells = [
            Cell(type=CellType.MARKDOWN, content="# Header", lineno=1),
            Cell(type=CellType.CODE, content="x = 42", lineno=2, counter=1, result=42),
        ]

        results = cells_to_json(cells)
        assert len(results) == 2
        assert results[0]["index"] == 0
        assert results[0]["type"] == "markdown"
        assert results[1]["index"] == 1
        assert results[1]["type"] == "code"
