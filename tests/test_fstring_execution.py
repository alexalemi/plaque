"""Tests for f-string execution and rendering."""

import io
from src.plaque.ast_parser import parse_ast
from src.plaque.processor import Processor
from src.plaque.formatter import render_cell
from src.plaque.cell import CellType


class TestFStringExecution:
    """Tests for f-string markdown cell execution."""

    def test_fstring_execution_basic(self):
        """Test basic f-string execution."""
        content = '''name = "World"
f"""# Hello {name}!
Welcome to the test."""
'''
        cells = list(parse_ast(io.StringIO(content)))

        # Process cells to execute them
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        # Check the f-string was executed
        assert len(processed_cells) == 2
        fstring_cell = processed_cells[1]
        assert fstring_cell.type == CellType.MARKDOWN
        assert fstring_cell.is_code is True
        assert fstring_cell.result == "# Hello World!\nWelcome to the test."
        assert fstring_cell.error is None

    def test_fstring_execution_with_expressions(self):
        """Test f-string with complex expressions."""
        content = '''x = 5
y = 10
f"""# Math Results
Sum: {x + y}
Product: {x * y}
List: {[i**2 for i in range(3)]}"""
'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        # Find the f-string cell
        fstring_cell = None
        for cell in processed_cells:
            if cell.metadata.get("string_prefix", "").startswith("f"):
                fstring_cell = cell
                break

        assert fstring_cell is not None
        assert "Sum: 15" in fstring_cell.result
        assert "Product: 50" in fstring_cell.result
        assert "List: [0, 1, 4]" in fstring_cell.result

    def test_fstring_execution_error(self):
        """Test f-string with undefined variable."""
        content = '''f"""Error: {undefined_var}"""'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        fstring_cell = processed_cells[0]
        assert fstring_cell.error is not None
        assert "NameError" in fstring_cell.error
        assert "undefined_var" in fstring_cell.error

    def test_fstring_rendering(self):
        """Test f-string rendering in HTML."""
        content = '''name = "Test"
f"""# Hello {name}"""
'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        # Render the f-string cell
        html = render_cell(processed_cells[1])

        # Check it renders as markdown with execution counter
        assert '<div class="markdown-content"' in html
        assert '<h1 id="hello-test">Hello Test</h1>' in html
        assert 'class="cell-counter"' in html
        assert ">1<" in html  # Execution counter

    def test_fstring_error_rendering(self):
        """Test f-string error rendering."""
        content = '''f"""Error: {undefined}"""'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        html = render_cell(processed_cells[0])

        # Check it renders as an error cell
        assert 'class="cell code-cell"' in html
        assert 'class="cell-error"' in html
        assert "ERROR" in html
        assert "NameError" in html
        assert 'class="cell-counter"' in html

    def test_raw_string_not_executed(self):
        """Test that raw strings are not executed."""
        content = r'''r"""Raw string with \n"""'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        # Raw strings should not be executed
        assert processed_cells[0].result is None
        assert processed_cells[0].error is None
        assert processed_cells[0].counter == 0

    def test_fstring_with_raw_prefix(self):
        """Test f-raw strings."""
        content = r'''path = "test"
fr"""Path: C:\Users\{path}"""
'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()
        processed_cells = processor.process_cells(cells)

        fstring_cell = processed_cells[1]
        assert fstring_cell.result == r"Path: C:\Users\test"
        assert r"C:\Users" in fstring_cell.result  # Backslashes preserved

    def test_fstring_dependency_tracking(self):
        """Test that f-strings participate in dependency tracking."""
        # Test that changing the variable that f-string depends on causes re-execution
        content = '''x = 1
f"""Value: {x}"""
'''
        cells = list(parse_ast(io.StringIO(content)))
        processor = Processor()

        # First run
        processed_cells = processor.process_cells(cells)
        assert "Value: 1" in processed_cells[1].result
        first_counter = processed_cells[1].counter

        # Change the value of x
        new_content = '''x = 2
f"""Value: {x}"""
'''
        new_cells = list(parse_ast(io.StringIO(new_content)))
        processed_cells = processor.process_cells(new_cells)

        # The f-string should show the new value
        assert "Value: 2" in processed_cells[1].result
        # And it should have been re-executed (different counter)
        assert processed_cells[1].counter != first_counter
