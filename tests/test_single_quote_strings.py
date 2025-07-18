"""Tests for single quote string detection in the AST parser."""

import io
from src.plaque.ast_parser import parse_ast, ASTParser
from src.plaque.cell import CellType


class TestSingleQuoteStrings:
    """Tests for single and double quote string detection."""

    def test_basic_single_quote_string(self):
        """Test basic single quote string as markdown cell."""
        content = "'This is a single quote string'"
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is a single quote string"
        assert cells[0].lineno == 1

    def test_basic_double_quote_string(self):
        """Test basic double quote string as markdown cell."""
        content = '"This is a double quote string"'
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is a double quote string"
        assert cells[0].lineno == 1

    def test_raw_single_quote_string(self):
        """Test raw single quote string."""
        content = "r'This is a raw string with \\n'"
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is a raw string with \\n"
        assert cells[0].metadata.get("string_prefix") == "r"

    def test_raw_double_quote_string(self):
        """Test raw double quote string."""
        content = 'r"This is a raw string with \\n"'
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 1
        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == "This is a raw string with \\n"
        assert cells[0].metadata.get("string_prefix") == "r"

    def test_fstring_single_quote(self):
        """Test f-string with single quotes."""
        content = """name = "World"
f'Hello {name}!'"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2

        # First cell: code
        assert cells[0].type == CellType.CODE
        assert cells[0].content == 'name = "World"'

        # Second cell: f-string (should be treated as code for execution)
        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].is_code  # f-strings should be executable
        assert cells[1].content == "f'Hello {name}!'"
        assert cells[1].metadata.get("string_prefix") == "f"

    def test_fstring_double_quote(self):
        """Test f-string with double quotes."""
        content = """name = "World"
f"Hello {name}!\""""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 2

        # First cell: code
        assert cells[0].type == CellType.CODE
        assert cells[0].content == 'name = "World"'

        # Second cell: f-string (should be treated as code for execution)
        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].is_code  # f-strings should be executable
        assert cells[1].content == 'f"Hello {name}!"'
        assert cells[1].metadata.get("string_prefix") == "f"

    def test_mixed_quote_types(self):
        """Test file with mixed quote types."""
        content = """x = 1

'Single quote markdown'

"Double quote markdown"

'''Triple single quote markdown'''

\"\"\"Triple double quote markdown\"\"\"

r'Raw single quote'

fr"Raw f-string with {x}"
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 7

        # First cell: code
        assert cells[0].type == CellType.CODE
        assert cells[0].content == "x = 1"

        # Second cell: single quote markdown
        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].content == "Single quote markdown"

        # Third cell: double quote markdown
        assert cells[2].type == CellType.MARKDOWN
        assert cells[2].content == "Double quote markdown"

        # Fourth cell: triple single quote markdown
        assert cells[3].type == CellType.MARKDOWN
        assert cells[3].content == "Triple single quote markdown"

        # Fifth cell: triple double quote markdown
        assert cells[4].type == CellType.MARKDOWN
        assert cells[4].content == "Triple double quote markdown"

        # Sixth cell: raw single quote
        assert cells[5].type == CellType.MARKDOWN
        assert cells[5].content == "Raw single quote"
        assert cells[5].metadata.get("string_prefix") == "r"

        # Seventh cell: raw f-string (executable)
        assert cells[6].type == CellType.MARKDOWN
        assert cells[6].is_code
        assert cells[6].content == 'fr"Raw f-string with {x}"'
        assert cells[6].metadata.get("string_prefix") == "fr"

    def test_strings_with_quotes_inside(self):
        """Test strings that contain quotes inside them."""
        content = """'String with "double quotes" inside'

"String with 'single quotes' inside"

'String with escaped \\'quotes\\''
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 3

        assert cells[0].type == CellType.MARKDOWN
        assert cells[0].content == 'String with "double quotes" inside'

        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].content == "String with 'single quotes' inside"

        assert cells[2].type == CellType.MARKDOWN
        assert cells[2].content == "String with escaped \\'quotes\\'"

    def test_assignment_vs_standalone_single_quotes(self):
        """Test that assigned strings are not treated as cells."""
        content = """x = 'This is assigned'
y = "This is also assigned"

'This is standalone'

"This is also standalone"
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 3

        # First cell: assignments (code)
        assert cells[0].type == CellType.CODE
        assert "x = 'This is assigned'" in cells[0].content
        assert 'y = "This is also assigned"' in cells[0].content

        # Second cell: standalone single quote
        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].content == "This is standalone"

        # Third cell: standalone double quote
        assert cells[2].type == CellType.MARKDOWN
        assert cells[2].content == "This is also standalone"

    def test_get_string_info_all_quote_types(self):
        """Test the _get_string_info method with all quote types."""
        parser = ASTParser()

        # Single quotes
        info = parser._get_string_info("'content'")
        assert info == ("", "'", 1)

        # Double quotes
        info = parser._get_string_info('"content"')
        assert info == ("", '"', 1)

        # Triple single quotes
        info = parser._get_string_info("'''content'''")
        assert info == ("", "'''", 3)

        # Triple double quotes
        info = parser._get_string_info('"""content"""')
        assert info == ("", '"""', 3)

        # Raw single quotes
        info = parser._get_string_info("r'content'")
        assert info == ("r", "'", 2)

        # Raw double quotes
        info = parser._get_string_info('r"content"')
        assert info == ("r", '"', 2)

        # F-string single quotes
        info = parser._get_string_info("f'content'")
        assert info == ("f", "'", 2)

        # F-string double quotes
        info = parser._get_string_info('f"content"')
        assert info == ("f", '"', 2)

        # Combined prefixes
        info = parser._get_string_info("fr'content'")
        assert info == ("fr", "'", 3)

        info = parser._get_string_info('rf"content"')
        assert info == ("rf", '"', 3)

        # Case insensitive prefixes
        info = parser._get_string_info("F'content'")
        assert info == ("f", "'", 2)

        info = parser._get_string_info('R"content"')
        assert info == ("r", '"', 2)

    def test_single_quote_with_code_cells(self):
        """Test single quote strings mixed with traditional code cells."""
        content = """# %% First cell
x = 1

'Markdown cell'

# %% Another code cell
y = 2

"Another markdown cell"
"""
        cells = list(parse_ast(io.StringIO(content)))
        assert len(cells) == 4

        # First cell: marked code cell
        assert cells[0].type == CellType.CODE
        assert cells[0].content == "x = 1"
        assert cells[0].metadata.get("title") == "First cell"

        # Second cell: single quote markdown
        assert cells[1].type == CellType.MARKDOWN
        assert cells[1].content == "Markdown cell"

        # Third cell: marked code cell
        assert cells[2].type == CellType.CODE
        assert cells[2].content == "y = 2"
        assert cells[2].metadata.get("title") == "Another code cell"

        # Fourth cell: double quote markdown
        assert cells[3].type == CellType.MARKDOWN
        assert cells[3].content == "Another markdown cell"
