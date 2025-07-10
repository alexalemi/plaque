"""Tests for the AST parser module."""

import pytest
import io
from src.plaque.ast_parser import parse_ast, ASTParser
from src.plaque.cell import Cell, CellType


class TestASTParser:
    """Tests for the AST parser."""

    def test_empty_file(self):
        """Test parsing empty file."""
        cells = list(parse_ast(io.StringIO("")))
        assert len(cells) == 0

    def test_single_code_cell(self):
        """Test parsing single code cell."""
        content = "x = 1\ny = 2\n"
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.CODE
        assert cells[0].content == "x = 1\ny = 2"
        assert cells[0].lineno == 1

    def test_multiple_code_cells(self):
        """Test parsing multiple code cells."""
        content = """x = 1
y = 2

# %%

z = 3
w = 4
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.CODE
        assert cells[0].content == "x = 1\ny = 2"
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "z = 3\nw = 4"

    def test_cell_with_title(self):
        """Test parsing cell with title."""
        content = """# %% Test Cell
x = 1
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].metadata == {"title": "Test Cell"}

    def test_markdown_cell_basic(self):
        """Test parsing basic markdown cell."""
        content = """# %% [markdown]
# This is a header
# This is content
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        # Note: AST parser doesn't handle markdown comment stripping like legacy parser
        assert "This is a header" in cells[0].content

    def test_triple_double_quote_markdown(self):
        """Test triple double quote markdown."""
        content = '''"""This is markdown content"""
x = 1
'''
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is markdown content"
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"

    def test_triple_single_quote_markdown(self):
        """Test triple single quote markdown."""
        content = """'''This is markdown content'''
x = 1
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is markdown content"
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"

    def test_multiline_triple_quote_markdown(self):
        """Test multiline triple quote markdown."""
        content = '''"""
This is multiline
markdown content
"""
x = 1
'''
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert "This is multiline" in cells[0].content
        assert "markdown content" in cells[0].content
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"

    def test_mixed_boundaries(self):
        """Test file with both # %% and triple quote boundaries."""
        content = '''"""
# Introduction
This is the introduction
"""

x = 1

# %% Data Processing
y = x * 2

"""
# Results
The result is computed
"""

z = y + 1
'''
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 5

        # First cell: markdown
        assert cells[0].type == CellType.MARKDOWN
        assert "Introduction" in cells[0].content

        # Second cell: code
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"

        # Third cell: code with title
        assert cells[2].type == CellType.CODE
        assert cells[2].content == "y = x * 2"
        assert cells[2].metadata.get("title") == "Data Processing"

        # Fourth cell: markdown
        assert cells[3].type == CellType.MARKDOWN
        assert "Results" in cells[3].content

        # Fifth cell: code
        assert cells[4].type == CellType.CODE
        assert cells[4].content == "z = y + 1"

    def test_cell_boundary_parsing(self):
        """Test cell boundary parsing with various formats."""
        parser = ASTParser()

        # Basic boundary
        title, cell_type, metadata = parser.parse_cell_boundary("# %%")
        assert title == ""
        assert cell_type == CellType.CODE
        assert metadata == {}

        # With title
        title, cell_type, metadata = parser.parse_cell_boundary("# %% Test Title")
        assert title == "Test Title"
        assert cell_type == CellType.CODE
        assert metadata == {}

        # With markdown type
        title, cell_type, metadata = parser.parse_cell_boundary("# %% [markdown]")
        assert title == ""
        assert cell_type == CellType.MARKDOWN
        assert metadata == {}

        # With title and markdown
        title, cell_type, metadata = parser.parse_cell_boundary(
            "# %% Test Title [markdown]"
        )
        assert title == "Test Title"
        assert cell_type == CellType.MARKDOWN
        assert metadata == {}

        # With metadata
        title, cell_type, metadata = parser.parse_cell_boundary(
            '# %% Test Title key="value"'
        )
        assert title == "Test Title"
        assert cell_type == CellType.CODE
        assert metadata == {"key": "value"}

    def test_complex_example(self):
        """Test with the simple.py example."""
        with open("examples/simple.py", "r") as f:
            cells = list(parse_ast(f))

        assert len(cells) == 5

        # First cell: function definition
        assert cells[0].type == CellType.CODE
        assert "def foo(x):" in cells[0].content

        # Second cell: variable assignment
        assert cells[1].type == CellType.CODE
        assert cells[1].content.strip() == "y = 3"

        # Third cell: function call
        assert cells[2].type == CellType.CODE
        assert cells[2].content.strip() == "foo(1)"

        # Fourth cell: function call with variable
        assert cells[3].type == CellType.CODE
        assert cells[3].content.strip() == "foo(y)"

        # Fifth cell: markdown
        assert cells[4].type == CellType.MARKDOWN
        assert "I don't know what else to do." in cells[4].content

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in source code."""
        # Code with syntax error should still parse cell boundaries
        content = """x = 1

# %% 
def invalid_syntax(
    # Missing closing parenthesis

y = 2
"""
        cells = list(parse_ast(io.StringIO(content)))
        # Should still detect the boundaries even with syntax error
        assert len(cells) >= 2
        assert cells[0].content == "x = 1"

    def test_nested_quotes(self):
        """Test handling of nested quotes."""
        content = '''"""This has "nested" quotes"""
x = "string with \\"escaped\\" quotes"
'''
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert "nested" in cells[0].content
        assert cells[1].type == CellType.CODE
        assert "escaped" in cells[1].content

    def test_assignment_vs_standalone_string(self):
        """Test that AST parser correctly distinguishes assignments from standalone strings."""
        content = '''# Test assignment vs standalone
var = """This is an assignment"""

"""This is a standalone string"""

x = 1
'''
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 3

        # First cell: code with assignment
        assert cells[0].type == CellType.CODE
        assert "var = " in cells[0].content

        # Second cell: markdown from standalone string
        assert cells[1].type == CellType.MARKDOWN
        assert "This is a standalone string" in cells[1].content

        # Third cell: code
        assert cells[2].type == CellType.CODE
        assert cells[2].content == "x = 1"

    def test_empty_cells(self):
        """Test handling of empty cells."""
        content = """# %%

# %%
x = 1
"""
        cells = list(parse_ast(io.StringIO(content)))
        # Empty cells should not be yielded
        assert len(cells) == 1
        assert cells[0].content.strip() == "x = 1"

    def test_line_numbers(self):
        """Test that line numbers are tracked correctly."""
        content = """# %% First Cell
x = 1

# %% Second Cell
y = 2
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].lineno == 1
        assert cells[1].lineno == 4
