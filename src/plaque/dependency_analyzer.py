"""Dependency analyzer for plaque notebook cells.

This module analyzes Python code cells to determine:
1. Which variables/names each cell provides (defines)
2. Which variables/names each cell requires (uses)
3. Dependencies between cells based on variable usage
"""

import ast
from typing import Set, Dict, List, Tuple
from .cell import Cell


class VariableAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze variable usage in a cell."""

    def __init__(self):
        self.provides: Set[str] = set()
        self.requires: Set[str] = set()
        self.current_scope_names: Set[str] = set()
        self.in_function_def = False
        self.in_class_def = False

    def visit_Name(self, node: ast.Name):
        """Visit a name node (variable reference)."""
        if isinstance(node.ctx, ast.Store):
            # Variable is being assigned to
            self.provides.add(node.id)
            self.current_scope_names.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Variable is being read
            if node.id not in self.current_scope_names:
                # Only consider it a requirement if it's not defined in current scope
                self.requires.add(node.id)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit a function definition."""
        # Function name is provided at module level
        self.provides.add(node.name)

        # Visit function body in separate scope
        old_in_function = self.in_function_def
        old_scope_names = self.current_scope_names.copy()

        self.in_function_def = True
        # Add function parameters to local scope
        for arg in node.args.args:
            self.current_scope_names.add(arg.arg)

        # Visit function body
        for stmt in node.body:
            self.visit(stmt)

        # Restore previous scope
        self.in_function_def = old_in_function
        self.current_scope_names = old_scope_names

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit an async function definition."""
        # Same logic as regular function
        self.provides.add(node.name)

        old_in_function = self.in_function_def
        old_scope_names = self.current_scope_names.copy()

        self.in_function_def = True
        for arg in node.args.args:
            self.current_scope_names.add(arg.arg)

        for stmt in node.body:
            self.visit(stmt)

        self.in_function_def = old_in_function
        self.current_scope_names = old_scope_names

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit a class definition."""
        # Class name is provided at module level
        self.provides.add(node.name)

        # Visit class body in separate scope
        old_in_class = self.in_class_def
        old_scope_names = self.current_scope_names.copy()

        self.in_class_def = True

        # Visit class body
        for stmt in node.body:
            self.visit(stmt)

        # Restore previous scope
        self.in_class_def = old_in_class
        self.current_scope_names = old_scope_names

    def visit_Import(self, node: ast.Import):
        """Visit an import statement."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # Handle dotted imports (e.g., import os.path -> provides 'os')
            if "." in name:
                name = name.split(".")[0]
            self.provides.add(name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit a from...import statement."""
        for alias in node.names:
            if alias.name == "*":
                # Star import - can't determine what's provided
                continue
            name = alias.asname if alias.asname else alias.name
            self.provides.add(name)

        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        """Visit a for loop."""
        # The loop variable is provided in the current scope
        if isinstance(node.target, ast.Name):
            self.provides.add(node.target.id)
            self.current_scope_names.add(node.target.id)
        elif isinstance(node.target, ast.Tuple):
            # Handle tuple unpacking in for loops
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    self.provides.add(elt.id)
                    self.current_scope_names.add(elt.id)

        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        """Visit a list comprehension."""
        # Comprehensions have their own scope
        old_scope_names = self.current_scope_names.copy()
        # old_provides = self.provides.copy()

        # Add comprehension variables to local scope
        for generator in node.generators:
            if isinstance(generator.target, ast.Name):
                self.current_scope_names.add(generator.target.id)

        self.generic_visit(node)

        # Remove comprehension variables from provides (they don't leak out)
        for generator in node.generators:
            if isinstance(generator.target, ast.Name):
                self.provides.discard(generator.target.id)

        # Restore previous scope
        self.current_scope_names = old_scope_names

    def visit_SetComp(self, node: ast.SetComp):
        """Visit a set comprehension."""
        self.visit_ListComp(node)  # Same logic as list comprehension

    def visit_DictComp(self, node: ast.DictComp):
        """Visit a dictionary comprehension."""
        self.visit_ListComp(node)  # Same logic as list comprehension

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """Visit a generator expression."""
        self.visit_ListComp(node)  # Same logic as list comprehension

    def visit_With(self, node: ast.With):
        """Visit a with statement."""
        # Handle context manager variable assignment
        for item in node.items:
            if item.optional_vars:
                if isinstance(item.optional_vars, ast.Name):
                    self.provides.add(item.optional_vars.id)
                    self.current_scope_names.add(item.optional_vars.id)

        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        """Visit an async with statement."""
        # Same logic as regular with
        for item in node.items:
            if item.optional_vars:
                if isinstance(item.optional_vars, ast.Name):
                    self.provides.add(item.optional_vars.id)
                    self.current_scope_names.add(item.optional_vars.id)

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Visit an exception handler."""
        # Exception variable is provided in the handler scope
        if node.name:
            self.provides.add(node.name)
            self.current_scope_names.add(node.name)

        self.generic_visit(node)


def analyze_cell_dependencies(cell: Cell) -> Tuple[Set[str], Set[str]]:
    """Analyze a cell to determine what variables it provides and requires.

    Returns:
        Tuple of (provides, requires) sets
    """
    if not cell.is_code:
        # Markdown cells don't define or use variables
        return set(), set()

    try:
        tree = ast.parse(cell.content)
        analyzer = VariableAnalyzer()
        analyzer.visit(tree)

        # Filter out built-in names and common imports
        builtin_names = {
            "print",
            "len",
            "range",
            "list",
            "dict",
            "set",
            "tuple",
            "str",
            "int",
            "float",
            "bool",
            "type",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "min",
            "max",
            "sum",
            "abs",
            "round",
            "sorted",
            "reversed",
            "enumerate",
            "zip",
            "map",
            "filter",
            "any",
            "all",
            "open",
            "input",
            "iter",
            "next",
            "Exception",
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "True",
            "False",
            "None",
            "__name__",
            "__main__",
        }

        # Filter out builtins from requires
        requires = analyzer.requires - builtin_names

        return analyzer.provides, requires

    except SyntaxError:
        # If we can't parse the cell, assume it doesn't provide or require anything
        return set(), set()


def build_dependency_graph(cells: List[Cell]) -> Dict[int, Set[int]]:
    """Build a dependency graph showing which cells depend on which other cells.

    Returns:
        Dictionary mapping cell index to set of cell indices it depends on
    """
    # First, analyze all cells to determine their provides/requires
    for i, cell in enumerate(cells):
        provides, requires = analyze_cell_dependencies(cell)
        cell.provides = provides
        cell.requires = requires
        cell.update_content_hash()

    # Build dependency graph
    dependency_graph = {}

    for i, cell in enumerate(cells):
        dependencies = set()

        # For each variable this cell requires
        for var in cell.requires:
            # Find the most recent cell that provides this variable
            for j in range(i - 1, -1, -1):  # Search backwards
                if var in cells[j].provides:
                    dependencies.add(j)
                    break

        cell.depends_on = dependencies
        dependency_graph[i] = dependencies

    return dependency_graph


def find_cells_to_rerun(cells: List[Cell], changed_cell_indices: Set[int]) -> Set[int]:
    """Find all cells that need to be rerun based on changed cells.

    Args:
        cells: List of all cells
        changed_cell_indices: Set of indices of cells that have changed

    Returns:
        Set of cell indices that need to be rerun
    """
    to_rerun = set(changed_cell_indices)

    # Keep adding cells that depend on cells we need to rerun
    changed = True
    while changed:
        changed = False
        for i, cell in enumerate(cells):
            if i not in to_rerun and cell.depends_on & to_rerun:
                to_rerun.add(i)
                changed = True

    return to_rerun


def detect_changed_cells(old_cells: List[Cell], new_cells: List[Cell]) -> Set[int]:
    """Detect which cells have changed between two versions.

    Args:
        old_cells: Previous version of cells
        new_cells: New version of cells

    Returns:
        Set of indices of cells that have changed
    """
    changed = set()

    # Compare up to the minimum length
    min_len = min(len(old_cells), len(new_cells))

    for i in range(min_len):
        if old_cells[i].content != new_cells[i].content:
            changed.add(i)

    # If the number of cells changed, consider all new cells as changed
    if len(new_cells) > len(old_cells):
        for i in range(len(old_cells), len(new_cells)):
            changed.add(i)

    return changed
