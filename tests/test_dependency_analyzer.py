"""Tests for the dependency analyzer module."""

from src.plaque.dependency_analyzer import (
    analyze_cell_dependencies,
    build_dependency_graph,
    find_cells_to_rerun,
    detect_changed_cells,
)
from src.plaque.cell import Cell, CellType
from src.plaque.ast_parser import parse_ast


class TestVariableAnalyzer:
    """Tests for the VariableAnalyzer class."""

    def test_simple_assignment(self):
        """Test simple variable assignment."""
        cell = Cell(CellType.CODE, "x = 1", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"x"}
        assert requires == set()

    def test_variable_usage(self):
        """Test variable usage."""
        cell = Cell(CellType.CODE, "y = x + 1", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"y"}
        assert requires == {"x"}

    def test_function_definition(self):
        """Test function definition."""
        cell = Cell(CellType.CODE, "def foo(x):\n    return x + 1", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"foo"}
        assert requires == set()

    def test_function_call(self):
        """Test function call."""
        cell = Cell(CellType.CODE, "result = foo(5)", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"result"}
        assert requires == {"foo"}

    def test_import_statements(self):
        """Test import statements."""
        cell = Cell(CellType.CODE, "import os\nfrom math import sqrt", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"os", "sqrt"}
        assert requires == set()

    def test_import_with_alias(self):
        """Test import with alias."""
        cell = Cell(
            CellType.CODE, "import numpy as np\nfrom pandas import DataFrame as df", 1
        )
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"np", "df"}
        assert requires == set()

    def test_for_loop_variable(self):
        """Test for loop variable."""
        cell = Cell(CellType.CODE, "for i in range(10):\n    print(i)", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"i"}
        assert requires == set()  # range and print are builtins

    def test_tuple_unpacking(self):
        """Test tuple unpacking."""
        cell = Cell(CellType.CODE, "a, b = (1, 2)", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"a", "b"}
        assert requires == set()

    def test_class_definition(self):
        """Test class definition."""
        cell = Cell(CellType.CODE, "class MyClass:\n    pass", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"MyClass"}
        assert requires == set()

    def test_with_statement(self):
        """Test with statement."""
        cell = Cell(
            CellType.CODE, "with open('file.txt') as f:\n    content = f.read()", 1
        )
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"f", "content"}
        assert requires == set()  # open is a builtin

    def test_list_comprehension(self):
        """Test list comprehension."""
        cell = Cell(CellType.CODE, "result = [x * 2 for x in numbers]", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"result"}
        assert requires == {"numbers"}

    def test_exception_handling(self):
        """Test exception handling."""
        cell = Cell(
            CellType.CODE, "try:\n    x = 1\nexcept Exception as e:\n    print(e)", 1
        )
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"x", "e"}
        assert requires == set()  # Exception and print are builtins

    def test_builtin_filtering(self):
        """Test that builtin functions are filtered out."""
        cell = Cell(CellType.CODE, "result = len([1, 2, 3])", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == {"result"}
        assert requires == set()  # len should be filtered out

    def test_markdown_cell(self):
        """Test that markdown cells have no dependencies."""
        cell = Cell(CellType.MARKDOWN, "# This is markdown", 1)
        provides, requires = analyze_cell_dependencies(cell)
        assert provides == set()
        assert requires == set()

    def test_syntax_error_handling(self):
        """Test handling of syntax errors."""
        cell = Cell(
            CellType.CODE, "def invalid_syntax(\n    # Missing closing parenthesis", 1
        )
        provides, requires = analyze_cell_dependencies(cell)
        # Should return empty sets for syntax errors
        assert provides == set()
        assert requires == set()


class TestDependencyGraph:
    """Tests for dependency graph building."""

    def test_simple_dependency_chain(self):
        """Test simple dependency chain."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = x + 1", 2),
            Cell(CellType.CODE, "z = y * 2", 3),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()  # x depends on nothing
        assert dependency_graph[1] == {0}  # y depends on x
        assert dependency_graph[2] == {1}  # z depends on y

    def test_multiple_dependencies(self):
        """Test cell with multiple dependencies."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2),
            Cell(CellType.CODE, "z = x + y", 3),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()  # x depends on nothing
        assert dependency_graph[1] == set()  # y depends on nothing
        assert dependency_graph[2] == {0, 1}  # z depends on both x and y

    def test_function_dependency(self):
        """Test function definition and usage."""
        cells = [
            Cell(CellType.CODE, "def foo(x):\n    return x + 1", 1),
            Cell(CellType.CODE, "result = foo(5)", 2),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()  # function def depends on nothing
        assert dependency_graph[1] == {0}  # function call depends on definition

    def test_no_dependencies(self):
        """Test independent cells."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = 2", 2),
            Cell(CellType.CODE, "z = 3", 3),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()
        assert dependency_graph[1] == set()
        assert dependency_graph[2] == set()

    def test_markdown_cells(self):
        """Test that markdown cells have no dependencies."""
        cells = [
            Cell(CellType.MARKDOWN, "# Introduction", 1),
            Cell(CellType.CODE, "x = 1", 2),
            Cell(CellType.MARKDOWN, "# Results", 3),
            Cell(CellType.CODE, "y = x + 1", 4),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()  # markdown
        assert dependency_graph[1] == set()  # x = 1
        assert dependency_graph[2] == set()  # markdown
        assert dependency_graph[3] == {1}  # y depends on x

    def test_variable_overriding(self):
        """Test that variable overriding works correctly."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "x = 2", 2),  # Override x
            Cell(CellType.CODE, "y = x + 1", 3),
        ]

        dependency_graph = build_dependency_graph(cells)

        assert dependency_graph[0] == set()
        assert dependency_graph[1] == set()
        assert dependency_graph[2] == {1}  # y depends on the most recent x


class TestCellRerunLogic:
    """Tests for determining which cells to rerun."""

    def test_find_cells_to_rerun_simple(self):
        """Test finding cells to rerun in simple case."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = x + 1", 2),
            Cell(CellType.CODE, "z = y * 2", 3),
        ]

        build_dependency_graph(cells)  # Populate dependencies

        # If cell 0 changes, all cells should rerun
        to_rerun = find_cells_to_rerun(cells, {0})
        assert to_rerun == {0, 1, 2}

        # If cell 1 changes, cells 1 and 2 should rerun
        to_rerun = find_cells_to_rerun(cells, {1})
        assert to_rerun == {1, 2}

        # If cell 2 changes, only cell 2 should rerun
        to_rerun = find_cells_to_rerun(cells, {2})
        assert to_rerun == {2}

    def test_find_cells_to_rerun_complex(self):
        """Test finding cells to rerun in complex case."""
        cells = [
            Cell(CellType.CODE, "x = 1", 1),  # 0
            Cell(CellType.CODE, "y = 2", 2),  # 1
            Cell(CellType.CODE, "z = x + y", 3),  # 2 depends on 0, 1
            Cell(CellType.CODE, "w = x * 2", 4),  # 3 depends on 0
            Cell(CellType.CODE, "v = z + w", 5),  # 4 depends on 2, 3
        ]

        build_dependency_graph(cells)

        # If cell 0 changes, cells 0, 2, 3, 4 should rerun
        to_rerun = find_cells_to_rerun(cells, {0})
        assert to_rerun == {0, 2, 3, 4}

        # If cell 1 changes, cells 1, 2, 4 should rerun
        to_rerun = find_cells_to_rerun(cells, {1})
        assert to_rerun == {1, 2, 4}

    def test_detect_changed_cells(self):
        """Test detecting changed cells."""
        old_cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = x + 1", 2),
            Cell(CellType.CODE, "z = y * 2", 3),
        ]

        new_cells = [
            Cell(CellType.CODE, "x = 1", 1),  # unchanged
            Cell(CellType.CODE, "y = x + 2", 2),  # changed
            Cell(CellType.CODE, "z = y * 2", 3),  # unchanged
        ]

        changed = detect_changed_cells(old_cells, new_cells)
        assert changed == {1}

    def test_detect_changed_cells_new_cells(self):
        """Test detecting changed cells when new cells are added."""
        old_cells = [
            Cell(CellType.CODE, "x = 1", 1),
            Cell(CellType.CODE, "y = x + 1", 2),
        ]

        new_cells = [
            Cell(CellType.CODE, "x = 1", 1),  # unchanged
            Cell(CellType.CODE, "y = x + 1", 2),  # unchanged
            Cell(CellType.CODE, "z = y * 2", 3),  # new
        ]

        changed = detect_changed_cells(old_cells, new_cells)
        assert changed == {2}


class TestIntegration:
    """Integration tests using example files."""

    def test_simple_example_dependencies(self):
        """Test dependency analysis with simple.py example."""
        with open("examples/simple.py", "r") as f:
            cells = list(parse_ast(f))

        dependency_graph = build_dependency_graph(cells)

        # Cell 0: defines foo function
        assert cells[0].provides == {"foo"}
        assert cells[0].requires == set()

        # Cell 1: defines y variable
        assert cells[1].provides == {"y"}
        assert cells[1].requires == set()

        # Cell 2: uses foo function
        assert cells[2].provides == set()
        assert cells[2].requires == {"foo"}

        # Cell 3: uses both foo and y
        assert cells[3].provides == set()
        assert cells[3].requires == {"foo", "y"}

        # Cell 4: markdown, no dependencies
        assert cells[4].provides == set()
        assert cells[4].requires == set()

        # Check dependency graph
        assert dependency_graph[0] == set()  # foo def
        assert dependency_graph[1] == set()  # y def
        assert dependency_graph[2] == {0}  # foo(1) depends on foo
        assert dependency_graph[3] == {0, 1}  # foo(y) depends on foo and y
        assert dependency_graph[4] == set()  # markdown

    def test_rerun_optimization(self):
        """Test that rerun optimization works correctly."""
        with open("examples/simple.py", "r") as f:
            cells = list(parse_ast(f))

        build_dependency_graph(cells)

        # If we change cell 1 (y = 3), only cell 3 should need to rerun
        to_rerun = find_cells_to_rerun(cells, {1})
        assert to_rerun == {1, 3}  # y definition and foo(y) call

        # If we change cell 0 (foo definition), cells 2 and 3 should rerun
        to_rerun = find_cells_to_rerun(cells, {0})
        assert to_rerun == {0, 2, 3}  # foo def, foo(1), foo(y)

    def test_content_hash_tracking(self):
        """Test content hash tracking for change detection."""
        cell = Cell(CellType.CODE, "x = 1", 1)

        # Initially no hash
        assert cell.content_hash == ""

        # Update hash
        cell.update_content_hash()
        original_hash = cell.content_hash
        assert original_hash != ""

        # Content unchanged, hash should be same
        assert not cell.has_content_changed()

        # Change content
        cell.content = "x = 2"
        assert cell.has_content_changed()

        # Update hash again
        cell.update_content_hash()
        assert cell.content_hash != original_hash
