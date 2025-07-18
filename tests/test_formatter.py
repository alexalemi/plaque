"""Tests for the HTML formatter."""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from src.plaque.formatter import (
    format_code,
    format_markdown,
    format_result,
    render_cell,
    get_html_template,
    format,
    escape_html,
)
from src.plaque.cell import Cell, CellType


class TestEscapeHtml:
    """Test HTML escaping functionality."""

    def test_basic_escaping(self):
        """Test basic HTML character escaping."""
        text = "<script>alert('xss')</script>"
        result = escape_html(text)
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "alert(&#x27;xss&#x27;)" in result

    def test_ampersand_escaping(self):
        """Test ampersand escaping."""
        text = "Tom & Jerry"
        result = escape_html(text)
        assert "Tom &amp; Jerry" in result

    def test_quote_escaping(self):
        """Test quote escaping."""
        text = "He said \"Hello\" and 'Goodbye'"
        result = escape_html(text)
        assert "&quot;Hello&quot;" in result
        assert "&#x27;Goodbye&#x27;" in result

    def test_no_escaping_needed(self):
        """Test text that doesn't need escaping."""
        text = "Simple text with numbers 123"
        result = escape_html(text)
        assert result == text


class TestFormatCode:
    """Test code formatting with Pygments."""

    @patch("pygments.highlight")
    @patch("pygments.lexers.PythonLexer")
    @patch("pygments.formatters.HtmlFormatter")
    def test_pygments_highlighting(
        self, mock_formatter_class, mock_lexer_class, mock_highlight
    ):
        """Test Pygments syntax highlighting."""
        mock_lexer = Mock()
        mock_formatter = Mock()
        mock_lexer_class.return_value = mock_lexer
        mock_formatter_class.return_value = mock_formatter
        mock_highlight.return_value = '<span class="n">print</span><span class="p">(</span><span class="s2">"hello"</span><span class="p">)</span>'

        code = 'print("hello")'
        result = format_code(code)

        # Should call Pygments
        mock_lexer_class.assert_called_once()
        mock_formatter_class.assert_called_once()
        mock_highlight.assert_called_once_with(code, mock_lexer, mock_formatter)

        # Should wrap in pre/code tags
        assert result.startswith("<pre><code>")
        assert result.endswith("</code></pre>")
        assert "print" in result

    @patch("pygments.highlight", side_effect=ImportError("Pygments not available"))
    def test_pygments_fallback(self, mock_highlight):
        """Test fallback when Pygments is not available."""
        code = 'print("hello")'
        result = format_code(code)

        # Should fall back to escaped HTML
        assert "<pre><code>" in result
        assert "print(&quot;hello&quot;)" in result

    def test_code_escaping_in_fallback(self):
        """Test that code is properly escaped in fallback mode."""
        with patch("pygments.highlight", side_effect=ImportError()):
            code = '<script>alert("xss")</script>'
            result = format_code(code)

            assert "&lt;script&gt;" in result
            assert "alert(&quot;xss&quot;)" in result


class TestFormatMarkdown:
    """Test markdown formatting."""

    @patch("markdown.Markdown")
    def test_markdown_conversion(self, mock_markdown_class):
        """Test markdown to HTML conversion."""
        mock_md = Mock()
        mock_markdown_class.return_value = mock_md
        mock_md.convert.return_value = "<h1>Hello World</h1>"

        content = "# Hello World"
        result = format_markdown(content)

        mock_markdown_class.assert_called_once()
        mock_md.convert.assert_called_once_with(content)
        assert "<h1>Hello World</h1>" in result

    @patch("markdown.Markdown")
    def test_latex_equation_support(self, mock_markdown_class):
        """Test that LaTeX equations are passed through unchanged for MathJax."""
        mock_md = Mock()
        mock_markdown_class.return_value = mock_md
        mock_md.convert.return_value = (
            "<p>Einstein discovered that $E = mc^2$ and $$F = ma$$</p>"
        )

        content = "Einstein discovered that $E = mc^2$ and $$F = ma$$"
        result = format_markdown(content)

        # LaTeX should be passed through unchanged for MathJax to handle
        assert "$E = mc^2$" in result
        assert "$$F = ma$$" in result

    @patch.dict("sys.modules", {"markdown": None})
    def test_markdown_fallback(self):
        """Test fallback when markdown library is not available."""
        content = "# Header\n\n**Bold** text with `code`"
        result = format_markdown(content)

        # Should still convert basic markdown
        assert "<h1>Header</h1>" in result
        assert "<strong>Bold</strong>" in result
        assert "<code>code</code>" in result

    def test_markdown_headers_fallback(self):
        """Test header conversion in fallback mode."""
        with patch.dict("sys.modules", {"markdown": None}):
            content = "# H1\n## H2\n### H3"
            result = format_markdown(content)

            assert "<h1>H1</h1>" in result
            assert "<h2>H2</h2>" in result
            assert "<h3>H3</h3>" in result

    def test_markdown_formatting_fallback(self):
        """Test basic formatting in fallback mode."""
        with patch.dict("sys.modules", {"markdown": None}):
            content = "**bold** and *italic* text"
            result = format_markdown(content)

            assert "<strong>bold</strong>" in result
            assert "<em>italic</em>" in result


class TestFormatResult:
    """Test result formatting using display system."""

    @patch("src.plaque.formatter.to_renderable")
    def test_result_formatting(self, mock_to_renderable):
        """Test that format_result uses the display system to get a renderable."""
        from src.plaque.renderables import HTML

        # Mock the renderable object returned by the display system
        mock_to_renderable.return_value = HTML(
            '<div class="custom">Custom Result</div>'
        )

        result_obj = "test result"
        formatted = format_result(result_obj)

        mock_to_renderable.assert_called_once_with(result_obj)
        assert formatted == '<div class="custom">Custom Result</div>'

    def test_none_result(self):
        """Test formatting None result."""
        result = format_result(None)
        assert result == ""


class TestRenderCell:
    """Test individual cell rendering."""

    def test_code_cell_basic(self):
        """Test basic code cell rendering."""
        cell = Cell(CellType.CODE, 'print("hello")', 1)
        cell.result = "hello"

        with (
            patch("src.plaque.formatter.format_code") as mock_format_code,
            patch("src.plaque.formatter.format_result") as mock_format_result,
        ):
            mock_format_code.return_value = '<pre><code>print("hello")</code></pre>'
            mock_format_result.return_value = '<pre class="result-output">hello</pre>'

            result = render_cell(cell)

            # Should contain cell structure
            assert 'class="cell code-cell"' in result
            assert 'id="cell-1"' in result

            # Should contain input section
            assert 'class="cell-input"' in result
            assert 'class="code-content"' in result

            # Should contain output section
            assert 'class="cell-output"' in result
            assert 'class="output-content"' in result

            mock_format_code.assert_called_once_with('print("hello")')
            mock_format_result.assert_called_once_with("hello", None, 0)

    def test_code_cell_with_title(self):
        """Test code cell with title metadata."""
        cell = Cell(CellType.CODE, "x = 42", 1, metadata={"title": "Assignment Cell"})

        with patch("src.plaque.formatter.format_code") as mock_format_code:
            mock_format_code.return_value = "<pre><code>x = 42</code></pre>"

            result = render_cell(cell)

            assert 'class="cell-title">Assignment Cell</div>' in result

    def test_code_cell_with_error(self):
        """Test code cell with error."""
        cell = Cell(CellType.CODE, "1 / 0", 1)
        cell.error = "ZeroDivisionError: division by zero"

        with patch("src.plaque.formatter.format_code") as mock_format_code:
            mock_format_code.return_value = "<pre><code>1 / 0</code></pre>"

            result = render_cell(cell)

            # Should contain error section
            assert 'class="cell-error"' in result
            assert 'class="error-label">Error:</div>' in result
            assert 'class="error-content"' in result
            assert "ZeroDivisionError: division by zero" in result

    def test_code_cell_no_result(self):
        """Test code cell with no result."""
        cell = Cell(CellType.CODE, "x = 42", 1)
        # cell.result is None by default

        with patch("src.plaque.formatter.format_code") as mock_format_code:
            mock_format_code.return_value = "<pre><code>x = 42</code></pre>"

            result = render_cell(cell)

            # Should not contain output section
            assert 'class="cell-output"' not in result
            assert 'class="output-label"' not in result

    def test_markdown_cell_basic(self):
        """Test basic markdown cell rendering."""
        cell = Cell(CellType.MARKDOWN, "# Hello World", 1)

        with patch("src.plaque.formatter.format_markdown") as mock_format_markdown:
            mock_format_markdown.return_value = "<h1>Hello World</h1>"

            result = render_cell(cell)

            # Should contain markdown content (no cell wrapper in new design)
            assert 'class="markdown-content"' in result
            assert 'id="cell-1"' in result
            assert "<h1>Hello World</h1>" in result

            mock_format_markdown.assert_called_once_with("# Hello World")

    def test_markdown_cell_with_title(self):
        """Test markdown cell with title metadata."""
        cell = Cell(
            CellType.MARKDOWN, "Some content", 1, metadata={"title": "Documentation"}
        )

        with patch("src.plaque.formatter.format_markdown") as mock_format_markdown:
            mock_format_markdown.return_value = "<p>Some content</p>"

            result = render_cell(cell)

            # In new design, titles become h3 headings
            assert 'class="markdown-title">Documentation</h3>' in result

    def test_empty_cell(self):
        """Test rendering empty/unknown cell type."""
        # This shouldn't happen in practice, but test defensive programming
        cell = Mock()
        cell.type = "UNKNOWN"

        result = render_cell(cell)
        assert result == ""


class TestHtmlTemplate:
    """Test HTML template handling."""

    def test_template_loading(self):
        """Test loading HTML template from file."""
        template_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>{content}</body>
</html>"""

        mock_file = mock_open(read_data=template_content)

        with patch("builtins.open", mock_file):
            result = get_html_template()

            assert result == template_content
            # Should have opened the correct template file
            mock_file.assert_called_once()
            call_args = mock_file.call_args[0]
            assert "templates/notebook.html" in call_args[0]

    def test_template_file_path(self):
        """Test that template path is constructed correctly."""
        with patch("builtins.open", mock_open(read_data="test")) as mock_file:
            get_html_template()

            # Should use path relative to formatter.py
            call_args = mock_file.call_args[0]
            path = call_args[0]
            assert path.endswith("templates/notebook.html")
            assert "src/plaque" in path


class TestCompleteFormat:
    """Test complete document formatting."""

    def test_format_with_template_substitution(self):
        """Test complete HTML generation with template."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.MARKDOWN, "# Test", 2),
        ]

        template_content = "<html><body>{content}</body></html>"

        with (
            patch(
                "src.plaque.formatter.get_html_template", return_value=template_content
            ),
            patch("src.plaque.formatter.render_cell") as mock_render,
        ):
            mock_render.side_effect = [
                '<div class="cell code-cell">Code Cell</div>',
                '<div class="cell markdown-cell">Markdown Cell</div>',
            ]

            result = format(cells)

            # Should substitute content into template
            assert result.startswith("<html><body>")
            assert result.endswith("</body></html>")
            assert "Code Cell" in result
            assert "Markdown Cell" in result

            # Should call render_cell for each cell
            assert mock_render.call_count == 2

    def test_format_empty_cells(self):
        """Test formatting with no cells."""
        cells = []
        template_content = "<html><body>{content}</body></html>"

        with patch(
            "src.plaque.formatter.get_html_template", return_value=template_content
        ):
            result = format(cells)

            assert result == "<html><body></body></html>"

    def test_format_mixed_cells(self):
        """Test formatting with mixed cell types."""
        code_cell = Cell(CellType.CODE, "print('hello')", 1)
        code_cell.result = "hello"

        markdown_cell = Cell(CellType.MARKDOWN, "# Title", 2)

        cells = [code_cell, markdown_cell]
        template_content = "<html>{content}</html>"

        with patch(
            "src.plaque.formatter.get_html_template", return_value=template_content
        ):
            result = format(cells)

            # Should contain code cell (markdown cells no longer have cell wrapper)
            assert "code-cell" in result
            assert (
                "markdown-content" in result
            )  # Markdown uses content wrapper, not cell wrapper
            assert "&#39;hello&#39;" in result
            assert "Title" in result


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_code_cell_pipeline(self):
        """Test complete code cell rendering pipeline."""
        cell = Cell(CellType.CODE, "x = 42\nx", 1, metadata={"title": "Test Cell"})
        cell.result = 42

        # Don't mock internal functions, test the real pipeline
        result = render_cell(cell)

        # Should have proper structure
        assert 'class="cell code-cell"' in result
        assert 'class="cell-title">Test Cell</div>' in result
        assert 'class="cell-input"' in result
        assert 'class="cell-output"' in result

        # Code should be syntax highlighted (if Pygments available)
        assert 'class="code-content"' in result

        # Result should be formatted
        assert "42" in result

    def test_full_markdown_cell_pipeline(self):
        """Test complete markdown cell rendering pipeline."""
        cell = Cell(CellType.MARKDOWN, "# Header\n\n**Bold** text", 1)

        # Don't mock internal functions, test the real pipeline
        result = render_cell(cell)

        # Should have proper structure (no cell wrapper in new design)
        assert 'class="markdown-content"' in result

        # Markdown should be converted (may vary based on markdown library availability)
        assert "Header" in result
        assert "Bold" in result or "bold" in result

    def test_error_cell_formatting(self):
        """Test error cell formatting with real error."""
        cell = Cell(CellType.CODE, "undefined_variable", 1)
        cell.error = "NameError: name 'undefined_variable' is not defined"

        result = render_cell(cell)

        # Should contain error formatting
        assert 'class="cell-error"' in result
        assert 'class="error-label"' in result
        assert 'class="error-content"' in result
        assert "NameError" in result
        assert "undefined_variable" in result

    def test_stdout_formatting(self):
        """Test stdout output formatting."""
        cell = Cell(CellType.CODE, 'print("Hello")', 1)
        cell.stdout = "Hello\n"

        result = render_cell(cell)

        # Should contain stdout formatting
        assert 'class="cell-stdout"' in result
        assert 'class="stdout-content"' in result
        assert "Hello" in result

    def test_stderr_formatting(self):
        """Test stderr output formatting."""
        cell = Cell(CellType.CODE, 'import sys; print("Error", file=sys.stderr)', 1)
        cell.stderr = "Error\n"

        result = render_cell(cell)

        # Should contain stderr formatting
        assert 'class="cell-stderr"' in result
        assert 'class="stderr-content"' in result
        assert "Error" in result

    def test_mixed_output_formatting(self):
        """Test formatting cell with stdout, stderr, and result."""
        cell = Cell(CellType.CODE, 'print("out"); print("err", file=sys.stderr); 42', 1)
        cell.stdout = "out\n"
        cell.stderr = "err\n"
        cell.result = 42

        result = render_cell(cell)

        # Should contain all output types
        assert 'class="cell-stdout"' in result
        assert 'class="cell-stderr"' in result
        assert 'class="cell-output"' in result
        assert "out" in result
        assert "err" in result
        assert "42" in result

    def test_output_escaping(self):
        """Test that stdout/stderr content is properly escaped."""
        cell = Cell(CellType.CODE, 'print("<script>alert(1)</script>")', 1)
        cell.stdout = "<script>alert(1)</script>\n"

        result = render_cell(cell)

        # Should escape HTML in output
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "<script>" not in result  # Should not contain raw script tag
