"""Tests for the parser module."""

import pytest
import io
from src.plaque.parser import parse_cell_boundary, parse
from src.plaque.cell import Cell, CellType


class TestParseCellBoundary:
    """Tests for parse_cell_boundary function."""
    
    def test_basic_cell_boundary(self):
        """Test basic cell boundary parsing."""
        title, cell_type, metadata = parse_cell_boundary("# %%")
        assert title == ""
        assert cell_type == CellType.CODE
        assert metadata == {}
    
    def test_cell_boundary_with_title(self):
        """Test cell boundary with title."""
        title, cell_type, metadata = parse_cell_boundary("# %% Test Title")
        assert title == "Test Title"
        assert cell_type == CellType.CODE
        assert metadata == {}
    
    def test_cell_boundary_with_markdown_type(self):
        """Test cell boundary with markdown type."""
        title, cell_type, metadata = parse_cell_boundary("# %% [markdown]")
        assert title == ""
        assert cell_type == CellType.MARKDOWN
        assert metadata == {}
    
    def test_cell_boundary_with_title_and_markdown(self):
        """Test cell boundary with both title and markdown type."""
        title, cell_type, metadata = parse_cell_boundary("# %% Test Title [markdown]")
        assert title == "Test Title"
        assert cell_type == CellType.MARKDOWN
        assert metadata == {}
    
    def test_cell_boundary_with_metadata(self):
        """Test cell boundary with metadata."""
        title, cell_type, metadata = parse_cell_boundary('# %% Test Title key="value" key2=value2')
        assert title == "Test Title"
        assert cell_type == CellType.CODE
        assert metadata == {"key": "value", "key2": "value2"}
    
    def test_cell_boundary_with_markdown_and_metadata(self):
        """Test cell boundary with markdown type and metadata."""
        title, cell_type, metadata = parse_cell_boundary('# %% [markdown] key="value"')
        assert title == ""
        assert cell_type == CellType.MARKDOWN
        assert metadata == {"key": "value"}
    
    def test_cell_boundary_whitespace_handling(self):
        """Test cell boundary with various whitespace."""
        title, cell_type, metadata = parse_cell_boundary("# %%   Test Title   [markdown]   key=value   ")
        assert title == "Test Title"
        assert cell_type == CellType.MARKDOWN
        assert metadata == {"key": "value"}
    
    def test_invalid_cell_boundary(self):
        """Test invalid cell boundary raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cell boundary line"):
            parse_cell_boundary("invalid line")


class TestParse:
    """Tests for the main parse function."""
    
    def test_empty_file(self):
        """Test parsing empty file."""
        cells = list(parse(io.StringIO("")))
        assert len(cells) == 0
    
    def test_single_code_cell(self):
        """Test parsing single code cell."""
        content = "x = 1\ny = 2\n"
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.CODE
        assert cells[0].content == "x = 1\ny = 2"
        assert cells[0].lineno == 0
    
    def test_multiple_code_cells(self):
        """Test parsing multiple code cells."""
        content = """x = 1
y = 2

# %%

z = 3
w = 4
"""
        cells = list(parse(io.StringIO(content)))
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
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].metadata == {"title": "Test Cell"}
    
    def test_markdown_cell_basic(self):
        """Test parsing basic markdown cell."""
        content = """# %% [markdown]
# This is a header
# This is content
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is a header\nThis is content"
    
    def test_markdown_cell_with_code_after(self):
        """Test markdown cell followed by code."""
        content = """# %% [markdown]
# This is markdown

x = 1
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is markdown"
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"
    
    def test_triple_double_quote_markdown(self):
        """Test triple double quote markdown."""
        content = '''"""This is markdown content"""
x = 1
'''
        cells = list(parse(io.StringIO(content)))
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
        cells = list(parse(io.StringIO(content)))
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
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is multiline\nmarkdown content"
        assert cells[1].type == CellType.CODE
        assert cells[1].content == "x = 1"
    
    def test_line_numbers(self):
        """Test that line numbers are tracked correctly."""
        content = """# %% First Cell
x = 1

# %% Second Cell
y = 2
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].lineno == 1  # First cell starts at line 1
        assert cells[1].lineno == 4  # Second cell starts at line 4


class TestIntegration:
    """Integration tests using actual example files."""
    
    def test_simple_example_file(self):
        """Test parsing the simple.py example file."""
        with open("examples/simple.py", "r") as f:
            cells = list(parse(f))
        
        assert len(cells) == 5
        
        # First cell: comment and function definition
        assert cells[0].type == CellType.CODE
        assert "A simple test" in cells[0].content
        assert "def foo(x):" in cells[0].content
        assert "return x + 1" in cells[0].content
        
        # Second cell: y = 3
        assert cells[1].type == CellType.CODE
        assert cells[1].content.strip() == "y = 3"
        
        # Third cell: foo(1)
        assert cells[2].type == CellType.CODE
        assert cells[2].content.strip() == "foo(1)"
        
        # Fourth cell: foo(y)
        assert cells[3].type == CellType.CODE
        assert cells[3].content.strip() == "foo(y)"
        
        # Fifth cell: markdown
        assert cells[4].type == CellType.MARKDOWN
        assert "I don't know what else to do." in cells[4].content
    
    def test_example_file_with_mixed_content(self):
        """Test parsing the example.py file with mixed content."""
        with open("examples/example.py", "r") as f:
            cells = list(parse(f))
        
        # Should have multiple cells with different types
        assert len(cells) > 3
        
        # Check that we have both code and markdown cells
        cell_types = [cell.type for cell in cells]
        assert CellType.CODE in cell_types
        assert CellType.MARKDOWN in cell_types
        
        # Look for specific content
        all_content = " ".join(cell.content for cell in cells)
        assert "square" in all_content  # Function name
        assert "matplotlib" in all_content  # Import
        
    def test_test_fixtures(self):
        """Test parsing our test fixture files."""
        # Test simple_cells.py
        with open("tests/test_fixtures/simple_cells.py", "r") as f:
            cells = list(parse(f))
        
        assert len(cells) == 3
        assert all(cell.type == CellType.CODE for cell in cells)
        
        # Test mixed_cells.py
        with open("tests/test_fixtures/mixed_cells.py", "r") as f:
            cells = list(parse(f))
        
        # Should have multiple cells with mixed types
        cell_types = [cell.type for cell in cells]
        assert CellType.CODE in cell_types
        assert CellType.MARKDOWN in cell_types


class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_empty_cells(self):
        """Test handling of empty cells."""
        content = """# %%

# %%
x = 1
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1  # Empty cells should not be yielded
        assert cells[0].content.strip() == "x = 1"
    
    def test_only_comments(self):
        """Test file with only comments."""
        content = """# This is a comment
# Another comment
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.CODE
        assert "This is a comment" in cells[0].content
    
    def test_unclosed_triple_quotes(self):
        """Test unclosed triple quotes."""
        content = '''"""This is unclosed
markdown content
x = 1
'''
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert "markdown content" in cells[0].content
        assert "x = 1" in cells[0].content
    
    def test_nested_quotes(self):
        """Test handling of nested quote patterns."""
        content = '''"""This has "nested" quotes"""
x = "string with \\"escaped\\" quotes"
'''
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 2
        assert cells[0].type == CellType.MARKDOWN
        assert 'nested' in cells[0].content
        assert cells[1].type == CellType.CODE
        assert 'escaped' in cells[1].content
    
    def test_cell_boundary_in_string(self):
        """Test cell boundaries that appear inside strings."""
        content = '''x = "# %% this is not a cell boundary"
y = 2
'''
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.CODE
        assert "this is not a cell boundary" in cells[0].content
    
    def test_unicode_content(self):
        """Test Unicode content handling."""
        content = """# %% Test with unicode
# Hello world in various languages
# 你好世界
# مرحبا بالعالم
# Привет мир

print("Hello 🌍")
"""
        cells = list(parse(io.StringIO(content)))
        assert len(cells) == 1
        assert "你好世界" in cells[0].content
        assert "🌍" in cells[0].content